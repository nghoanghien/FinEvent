# M5: Pattern Library

## Mục tiêu

Tạo thư viện pattern/few-shot examples từ AI-generated gold labels để giúp student LLM 8B sinh output đúng schema và đúng mức chi tiết.

## Input

```text
data/labels/events_gold.jsonl
data/processed/articles_clean.jsonl
PostgreSQL pgvector pattern embeddings
```

## Output

```text
data/patterns/patterns.jsonl
PostgreSQL table/index for event_patterns
reports/evaluation/pattern_metrics.csv
```

## Công nghệ

- JSONL.
- PostgreSQL nếu muốn query pattern có cấu trúc.
- pgvector index cho `event_patterns`.
- Embedding model mặc định.
- Pydantic/JSON Schema để đảm bảo pattern output hợp lệ.

## Cách triển khai chi tiết

### Bước 1: Convert gold event thành pattern

Mỗi pattern gồm:

- input excerpt.
- gold event output.
- event type/subtype.
- evidence span.
- explanation brief.
- teacher model.
- validation status.

### Bước 2: Chuẩn hóa pattern text

Pattern text dùng để embed nên bao gồm:

```text
Title: ...
Ticker/company: ...
Event type: ...
Evidence: ...
Summary: ...
Arguments: ...
```

Không embed toàn bộ bài nếu quá dài; ưu tiên đoạn evidence và summary.

### Bước 3: Validate pattern

Pattern chỉ được đưa vào store nếu:

- gold output đúng schema.
- có evidence.
- event type hợp lệ.
- nếu `NO_EVENT`, output phải có `events=[]`.

### Bước 4: Embed pattern

Lưu vào pgvector table/index `event_patterns`.

Metadata:

- pattern_id.
- event_type.
- event_subtype.
- ticker.
- source.
- document_label.

### Bước 5: Pattern selection

Khi xử lý bài mới, chọn pattern theo:

1. similarity vector.
2. event type hint.
3. ticker/company overlap.
4. argument overlap.
5. diversity để không lấy toàn pattern cùng một dạng nếu bài mơ hồ.

Mặc định lấy 3 pattern, tối đa 5.

## Kiểm thử

- Test pattern output parse được.
- Test pattern có metadata.
- Test search pattern trả top K.
- Test include `NO_EVENT` pattern khi input giống tin phân tích chung.

## Metrics

| Metric | Ý nghĩa |
| --- | --- |
| Pattern count | Số pattern pass validation |
| Coverage by event type | Số pattern theo event type |
| Pattern retrieval Recall@K | Pattern đúng loại có nằm trong top K không |
| Few-shot lift | F1 with patterns - F1 zero-shot |
| False positive reduction | NO_EVENT false positive giảm bao nhiêu |

## Done Criteria

- Có ít nhất 50 pattern pass validation.
- Có pattern cho ít nhất 6 event type.
- Có `NO_EVENT` pattern.
- Few-shot tốt hơn zero-shot trên ít nhất một metric chính.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Pattern quá dài làm loãng prompt | Chỉ giữ evidence và output JSON |
| Pattern retrieval sai loại | Thêm metadata filter/boost |
| Quá nhiều pattern làm 8B nhiễu | Giới hạn mặc định 3 |
| Không có pattern cho class hiếm | Crawl/gán nhãn bổ sung theo class |
