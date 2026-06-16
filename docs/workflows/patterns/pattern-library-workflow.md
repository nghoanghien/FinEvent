# Pattern Library Workflow

## Mục tiêu

Tạo thư viện ví dụ chuẩn gồm cặp:

```text
[Bài báo hoặc đoạn evidence] -> [Bảng sự kiện chuẩn]
```

Thư viện này dùng làm few-shot examples cho LLM 8B. Mục tiêu là giúp model nhỏ bắt chước cách trích xuất đúng schema, đúng taxonomy và đúng mức độ chi tiết.

## Input

Bài báo đã làm sạch:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "title": "HPG ký hợp đồng cung cấp thép cho dự án ...",
  "text": "Nội dung bài báo...",
  "source_url": "https://example.com/news"
}
```

Prompt cho teacher model:

```text
Bạn là chuyên gia phân tích tin doanh nghiệp Việt Nam.
Hãy đọc bài báo và trích xuất các sự kiện doanh nghiệp theo schema FinEvent-VN.
Chỉ dùng thông tin có trong bài. Nếu không có sự kiện cụ thể, trả NO_EVENT.
```

## Output

Pattern record:

```json
{
  "pattern_id": "pattern_contract_001",
  "article_id": "cafef_hpg_20260115_001",
  "event_type": "CONTRACT",
  "input_text": "Đoạn bài báo chứa sự kiện...",
  "gold_output": {
    "document_label": "HAS_EVENT",
    "events": []
  },
  "explanation_brief": "Bài báo nói về việc doanh nghiệp ký hợp đồng cụ thể...",
  "quality_status": "auto_validated",
  "teacher_model": "gemini-or-gpt-teacher",
  "teacher_prompt_version": "teacher_v1.0",
  "auto_validation_status": "passed",
  "validation_errors": [],
  "version": "v1"
}
```

## Công nghệ

- Teacher LLM mạnh: Gemini/GPT/Claude hoặc model lớn khác.
- JSON Schema/Pydantic để validate output.
- AI repair prompt để sửa output lỗi format/schema.
- PostgreSQL + pgvector table/index cho pattern embeddings.
- FAISS baseline nếu cần so sánh vector search tối giản.

## Cách hoạt động

### Bước 1: Chọn bài để tạo pattern

Ưu tiên:

- Bài có sự kiện rõ ràng.
- Bài đại diện cho từng `event_type`.
- Bài có evidence ngắn, ít mơ hồ.
- Bài có metadata tốt: source, ngày đăng, ticker.

Tập v1 nên có tối thiểu:

| Nhóm | Số pattern mục tiêu |
| --- | --- |
| `CONTRACT` | 10 |
| `CAPITAL` | 10 |
| `LEADERSHIP` | 8 |
| `EXPANSION` | 10 |
| `LEGAL_RISK` | 8 |
| `MA` / `PARTNERSHIP` / `LICENSE_APPROVAL` | 10-20 tổng |
| `NO_EVENT` | 10 |

### Bước 2: Teacher extraction

Teacher model sinh output theo [event-schema.md](../../schema/event-schema.md).

Prompt phải nhấn mạnh:

- Không bịa ticker.
- Không bịa chiều hướng tác động nếu bài không đủ bằng chứng.
- Evidence span phải lấy từ bài.
- Có thể trả nhiều event nếu bài có nhiều sự kiện.

### Bước 3: Schema validation

Tự động kiểm tra:

- JSON parse được.
- Enum hợp lệ.
- `events=[]` nếu `NO_EVENT`.
- Evidence span có trong bài hoặc gần khớp.
- Confidence hợp lệ.

Record lỗi được đưa vào bước AI repair. Nếu vẫn fail sau số lần retry cấu hình trước, record bị loại khỏi pattern store.

### Bước 4: AI repair and acceptance

Nếu output lỗi schema hoặc evidence không khớp, hệ thống gọi teacher model hoặc repair model với yêu cầu:

- Chỉ sửa JSON/field sai.
- Không thêm thông tin ngoài bài.
- Chọn lại evidence span từ văn bản gốc nếu evidence sai.
- Giữ taxonomy trong [event-schema.md](../../schema/event-schema.md).

Pattern được chấp nhận khi `auto_validation_status=passed`. Project không có bước kiểm tra thủ công; pattern đã pass validation được xem là pattern chuẩn vận hành.

### Bước 5: Pattern retrieval

Khi xử lý bài mới:

1. Tạo query từ bài mới, event keywords và event type hints.
2. Tìm pattern tương tự bằng pgvector theo vector và metadata.
3. Rerank pattern theo event type/subtype, ticker/company và argument overlap.
4. Chọn 3 pattern mặc định, tối đa 5 pattern nếu bài phức tạp.
5. Đưa pattern vào prompt extraction.

## Pattern Selection Rules

Mặc định chọn:

- 1 pattern có ticker/company hoặc ngành gần giống nếu có.
- 1-2 pattern có event keyword giống.
- 1 pattern khác loại để model phân biệt.
- 1 `NO_EVENT` pattern nếu bài đầu vào có vẻ là phân tích chung.

Không đưa quá nhiều pattern vì model 8B dễ bị loãng context.

## Metrics

| Metric | Ý nghĩa | Cách đo |
| --- | --- | --- |
| Pattern validity rate | Tỷ lệ pattern qua schema validation | valid / total |
| AI repair rate | Tỷ lệ teacher output cần repair | repaired / total |
| Rejection rate | Tỷ lệ pattern bị loại sau retry | rejected / total |
| Coverage by event type | Số pattern mỗi event type | count |
| Few-shot lift | Pattern giúp extraction tăng bao nhiêu | F1 with patterns - F1 zero-shot |
| Pattern retrieval precision | Pattern được chọn có liên quan không | AI-generated gold relevance |
| Pattern retrieval Recall@K | Pattern đúng loại có nằm trong top K không | event type/subtype match |

## Acceptance Criteria v1

- Có ít nhất 50 pattern AI-generated pass auto validation.
- Có pattern cho ít nhất 6 event type chính.
- Có `NO_EVENT` pattern để giảm false positive.
- Few-shot prompt với pattern phải tốt hơn zero-shot trên ít nhất một metric chính.

## Failure Cases

| Case | Cách xử lý |
| --- | --- |
| Teacher model sinh sai schema | Validate và retry với prompt sửa lỗi |
| Teacher bịa impact | Evidence check, hạ confidence bằng rule hoặc loại nếu không có evidence |
| Pattern quá dài | Cắt còn evidence span và summary |
| Pattern lệch taxonomy | Map lại theo taxonomy chuẩn |
| Retrieval chọn pattern không liên quan | Thêm rerank rule hoặc giới hạn event keyword |

## Artifact

```text
data/
  patterns/
    patterns_ai_generated.jsonl
    patterns_rejected.jsonl
  vector_store/
    pgvector_tables
    faiss/
      pattern_embeddings.faiss
```

Ví dụ pattern tối giản dùng trong prompt:

```json
{
  "input_excerpt": "Công ty A công bố ký hợp đồng trị giá 500 tỷ đồng...",
  "output": {
    "event_type": "CONTRACT",
    "impact_sentiment": "POSITIVE",
    "evidence_span": "ký hợp đồng trị giá 500 tỷ đồng"
  }
}
```
