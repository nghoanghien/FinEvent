# Workflow Bản Ghi Pattern

Workflow pattern-library cũ dùng vector index và retrieval path riêng cho patterns.
Luồng đó đã ngừng dùng.

Luồng hiện tại:

1. M02 tạo strict gold labels ở `data/labels/events_gold.jsonl`.
2. M03 build pattern records ở `data/patterns/patterns.jsonl`.
3. M03 map mỗi pattern vào chunk và ghi `data/processed/chunk_patterns.jsonl`.
4. M03 sync `event_patterns`, `financial_news_chunks.pattern_refs` và `financial_news_chunk_patterns`.
5. M04 retrieve chunks và đưa `pattern_refs` của từng chunk vào `data/retrieval/online_contexts.jsonl`.
6. M06 đọc M04 contexts và render matched patterns bên trong extraction prompt.

Workflow hiện tại không có artifact vector riêng cho patterns.

## Pattern Record Là Gì

Pattern record là bản ghi rút ra từ gold label để làm ví dụ có cấu trúc cho prompt.
Nó không phải rule cứng và không phải evidence độc lập.

Một pattern thường chứa:

- `pattern_id`;
- `article_id`;
- `pattern_kind`;
- `event_type`;
- `event_subtype`;
- `evidence_span`;
- compact gold output;
- validation errors nếu có.

Pattern chỉ được dùng tốt khi gắn với chunk chứa hoặc đại diện cho evidence span.

## Luồng Mapping

M03 mapping pattern vào chunk theo thứ tự ưu tiên:

1. Chunk cùng `article_id` và chứa `evidence_span`.
2. Paragraph chunk trước, rồi section chunk, rồi document chunk.
3. Nếu không match được evidence span, fallback về document chunk cùng article.
4. Nếu article không có document chunk, fallback về chunk đầu tiên cùng article.

Fallback giúp pipeline không crash, nhưng report/metrics vẫn cần cho biết pattern
mapping có yếu không.

## Cách M04/M06 Dùng Pattern

M04 không query pattern riêng. Khi M04 retrieve một chunk, context metadata mang theo
`pattern_refs` của chunk đó.

M06 render pattern dưới context tương ứng:

```text
retrieved_context
  text
  metadata
  matched_patterns
```

Cách này giúp prompt thấy ví dụ schema liên quan đến chính context đang được dùng,
thay vì một pattern rời rạc có thể không liên quan đến evidence.

## Điều Không Nên Làm

- Không tạo lại pattern vector store riêng cho M06.
- Không thêm config `pattern_count` vào M06.
- Không chọn pattern chỉ bằng cosine similarity độc lập với context chunk.
- Không dùng pattern để thay evidence span trong article.

Pattern chỉ là hỗ trợ prompt. Evidence cuối cùng vẫn phải nằm trong article text.
