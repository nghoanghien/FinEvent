# M05: Node Pattern Đã Ngừng Dùng

M05 không còn là workflow node đang hoạt động.

Thiết kế cũ embed event patterns riêng và chọn pattern bằng cosine similarity trong
lúc extraction. Luồng đó đã bị bỏ vì tạo hai kênh retrieval độc lập: một kênh cho
chunks và một kênh cho patterns. Thiết kế hiện tại giữ retrieval grounded trên article
chunks.

Hành vi hiện tại:

- M03 build `data/patterns/patterns.jsonl` từ strict gold labels.
- M03 gắn mỗi pattern vào chunk phù hợp và ghi `data/processed/chunk_patterns.jsonl`.
- `financial_news_chunks.pattern_refs` và `financial_news_chunk_patterns` lưu mapping chunk-pattern.
- M04 retrieve chunks và mang `pattern_refs` theo từng retrieval context.
- M06 dùng M04 contexts; M06 không chạy vector search riêng hoặc node chọn pattern riêng.

Baseline hiện tại không có artifact vector riêng cho patterns và không có bảng DB
vector riêng cho patterns.

## Lý Do Ngừng Node M05

M05 cũ làm một việc nghe hợp lý nhưng không phù hợp với flow hiện tại: embed patterns
riêng rồi retrieve patterns bằng cosine similarity khi extraction. Vấn đề là pattern
không phải evidence. Pattern chỉ là ví dụ/record được rút ra từ gold label. Nếu chọn
pattern bằng similarity riêng, prompt có thể nhận một pattern tốt về mặt ngữ nghĩa
nhưng không gắn với chunk evidence mà M04 đã retrieve.

Thiết kế hiện tại buộc pattern đi qua chunk:

```text
gold label -> pattern record -> matching chunk -> retrieved context -> M06 prompt
```

Như vậy nếu prompt dùng pattern nào thì cũng biết pattern đó đến từ context chunk nào.

## Artifact Hiện Tại

| Artifact | Sinh ở đâu | Vai trò |
| --- | --- | --- |
| `data/patterns/patterns.jsonl` | M03 | Pattern records hợp lệ từ gold labels |
| `data/patterns/patterns_rejected.jsonl` | M03 | Pattern bị reject vì thiếu evidence hoặc lỗi validation |
| `data/processed/chunk_patterns.jsonl` | M03 | Mapping chunk-pattern |
| `data/processed/chunks.jsonl` | M03 | Chunk records đã có `pattern_refs` |

M05 không còn sinh artifact riêng. Tài liệu này chỉ giữ lại để giải thích quyết định
kiến trúc và tránh hiểu nhầm vì tên milestone M05 từng tồn tại.

## DB Hiện Tại

| Bảng/cột | Nội dung |
| --- | --- |
| `event_patterns` | Pattern records từ gold labels |
| `financial_news_chunks.pattern_refs` | Pattern refs gắn trực tiếp trên chunk |
| `financial_news_chunk_patterns` | Mapping normalized giữa chunk và pattern |

Không có bảng vector riêng cho patterns trong baseline hiện tại.

## Tác Động Đến Graph

- Frontend không còn node `m05_patterns`.
- Backend registry không import `m05_patterns`.
- M03 phụ thuộc M02 để lấy gold labels và build patterns.
- M04 phụ thuộc M03 vì cần chunks đã có `pattern_refs`.
- M06 phụ thuộc M04 vì chỉ lấy matched patterns thông qua retrieval contexts.

Nếu sau này cần thêm pattern analytics, nên thêm vào M03/M08 hoặc report riêng, không
khôi phục một retrieval channel độc lập cho patterns.
