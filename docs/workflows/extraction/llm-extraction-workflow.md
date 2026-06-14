# LLM Extraction Workflow

## Mục tiêu

Dùng model 8B để đọc bài báo mới, kết hợp context retrieval và pattern library, rồi sinh bảng sự kiện đúng schema FinEvent-VN.

Workflow này là lõi của hệ thống demo.

## Input

```json
{
  "article": {
    "article_id": "input_001",
    "title": "PNJ bổ nhiệm Tổng giám đốc mới",
    "text": "Nội dung bài báo...",
    "source_url": "https://example.com/news",
    "published_at": "2026-06-13T09:00:00+07:00"
  },
  "retrieved_contexts": [],
  "patterns": [],
  "ticker_company_map": []
}
```

## Output

Output phải theo [event-schema.md](../../schema/event-schema.md).

```json
{
  "article_id": "input_001",
  "document_label": "HAS_EVENT",
  "events": [
    {
      "event_id": "input_001_e01",
      "ticker": "PNJ",
      "company_name": "Công ty Cổ phần Vàng bạc Đá quý Phú Nhuận",
      "event_type": "LEADERSHIP",
      "event_subtype": "CEO_APPOINTMENT",
      "event_summary": "PNJ bổ nhiệm Tổng giám đốc mới.",
      "event_arguments": {
        "person": "...",
        "role": "Tổng giám đốc",
        "time": "..."
      },
      "impact_sentiment": "NEUTRAL",
      "evidence_span": "PNJ bổ nhiệm ... giữ chức Tổng giám đốc",
      "source_url": "https://example.com/news",
      "published_at": "2026-06-13T09:00:00+07:00",
      "confidence": 0.78
    }
  ],
  "warnings": [],
  "model_info": {
    "model_name": "qwen-2.5-7b-instruct",
    "prompt_version": "v1.0",
    "run_id": "20260613_001"
  }
}
```

## Công nghệ

- LLM 8B instruct: Qwen 2.5 7B/8B, Llama 3 8B hoặc tương đương.
- LangGraph để điều phối workflow online nhiều node.
- Prompt template versioned.
- JSON Schema/Pydantic validation.
- Verification workflow trong [verification-hallucination-workflow.md](verification-hallucination-workflow.md).
- Optional constrained decoding nếu runtime hỗ trợ.
- Retry-on-invalid-output với prompt sửa lỗi.

## Cách hoạt động

### Bước 1: Pre-check

Trước khi gọi LLM:

- Kiểm tra text đủ dài.
- Chuẩn hóa title + body.
- Lấy ticker hints từ dictionary.
- Gắn context retrieval và pattern examples.
- Gắn retrieval trace từ [article-query-extraction-workflow.md](article-query-extraction-workflow.md).

Nếu text quá ngắn hoặc lỗi parse, trả warning thay vì ép extraction.

### Bước 2: Event existence detection

Model trả lời bài có sự kiện doanh nghiệp cụ thể hay không.

Output trung gian:

```json
{
  "document_label": "HAS_EVENT",
  "reason": "Bài báo nêu việc doanh nghiệp ký hợp đồng cụ thể.",
  "evidence_candidates": [
    "câu hoặc đoạn có bằng chứng"
  ]
}
```

Nếu `NO_EVENT`, workflow dừng sớm và trả `events=[]`.

### Bước 3: Entity and ticker grounding

Model xác định:

- Tên công ty.
- Mã cổ phiếu nếu có.
- Các đối tác, dự án, cá nhân liên quan.

Ticker phải được kiểm tra với dictionary. Nếu chỉ thấy tên công ty nhưng mapping không chắc, để `ticker=null` và thêm warning.

### Bước 4: Event classification

Model phân loại event type theo taxonomy.

Prompt phải đưa danh sách enum và định nghĩa ngắn.

Nếu event không khớp nhóm nào:

- Dùng `OTHER` chỉ khi có sự kiện rõ.
- Ghi `event_subtype`.
- Confidence thấp hơn.

### Bước 5: Argument extraction

Model rút trích các slot có trong bài:

- Giá trị tiền.
- Đối tác.
- Dự án.
- Địa điểm.
- Thời gian.
- Nhân sự/chức danh.
- Cơ quan pháp lý.

Không có thì để `null` hoặc bỏ key.

### Bước 6: Impact assessment

Model đánh giá `impact_sentiment`, tức chiều hướng tác động của sự kiện.

Quy tắc:

- `LEGAL_RISK` thường nghiêng `NEGATIVE`, nhưng vẫn cần evidence.
- `CONTRACT`, `LICENSE_APPROVAL`, `EXPANSION` thường nghiêng `POSITIVE`.
- `LEADERSHIP` thường `NEUTRAL` nếu bài không nêu tác động.
- Nếu chỉ là công bố thông tin, không suy diễn quá mức.

### Bước 7: Final JSON generation

Model sinh JSON cuối cùng, không kèm markdown.

Yêu cầu prompt:

```text
Return only valid JSON. Do not include explanation outside JSON.
Every event must include evidence_span copied from the article.
If uncertain, set confidence below 0.6 and add warning.
```

### Bước 8: Validation and repair

Nếu JSON lỗi:

1. Parse fail -> gọi repair prompt chỉ sửa format, không thay đổi nội dung.
2. Enum lỗi -> map về enum gần nhất hoặc trả validation error.
3. Evidence thiếu -> yêu cầu model chọn evidence từ bài gốc.
4. Vẫn lỗi sau retry -> trả `UNCERTAIN` và log.

Sau bước sửa format/schema, phải chạy thêm verification:

- evidence span có nằm trong article/context không?
- event arguments có được evidence hỗ trợ không?
- event type/subtype có khớp taxonomy không?
- field không có căn cứ phải bị loại hoặc set `null`.

Chi tiết nằm trong [verification-hallucination-workflow.md](verification-hallucination-workflow.md).

## Prompt Structure v1

Prompt gồm 5 phần:

1. System role: chuyên gia trích xuất sự kiện doanh nghiệp.
2. Schema: JSON schema rút gọn.
3. Taxonomy: event types, subtypes, argument rules và impact sentiment rules.
4. Retrieved evidence contexts: top 3-5 context đã rerank.
5. Few-shot patterns: 3 ví dụ mặc định.
6. Input article: title + text + metadata.
7. Grounding instruction: chỉ sinh field có evidence.

## Metrics

| Metric | Ý nghĩa |
| --- | --- |
| JSON validity rate | Tỷ lệ output parse được |
| Schema compliance rate | Tỷ lệ output đúng enum/field |
| Event detection F1 | Có/không có event |
| Event type macro-F1 | Phân loại event type |
| Ticker accuracy | Mã cổ phiếu đúng |
| Argument partial match | Slot argument đúng một phần |
| Impact sentiment F1 | Sắc thái tác động |
| Evidence accuracy | Evidence có hỗ trợ event không |
| Hallucination rate | Tỷ lệ field không có trong bài |

## Acceptance Criteria v1

- JSON validity rate >= 95% sau repair.
- Event detection F1 >= 0.75 trên AI-generated gold set nhỏ.
- Event type macro-F1 có báo cáo theo từng class.
- Hallucination rate được đo và có error analysis.

## Failure Cases

| Case | Cách xử lý |
| --- | --- |
| Model sinh markdown thay vì JSON | Repair prompt hoặc regex extract JSON |
| Model bịa ticker | Cross-check dictionary, hạ confidence |
| Bài có nhiều công ty | Sinh nhiều event nếu mỗi công ty có sự kiện riêng |
| Bài phân tích chung | Trả `NO_EVENT` |
| Event type mơ hồ | Dùng `UNCERTAIN` hoặc `OTHER` với confidence thấp |
| Evidence không khớp | Retry chọn evidence, nếu vẫn lỗi thì reject event |

## Logging

Mỗi lần chạy lưu:

```json
{
  "run_id": "20260613_001",
  "article_id": "input_001",
  "prompt_version": "v1.0",
  "model_name": "qwen-2.5-7b-instruct",
  "retrieval_config": "hybrid_v1",
  "patterns_used": ["pattern_contract_001"],
  "raw_model_output": "...",
  "validated_output": {},
  "validation_errors": [],
  "latency_ms": 5200
}
```
