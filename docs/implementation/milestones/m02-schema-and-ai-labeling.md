# M2: Event Schema and AI-generated Gold Labels

## Mục tiêu

Tạo tập nhãn vận hành cho project bằng teacher LLM theo [event-schema.md](../../schema/event-schema.md). Nhãn được chấp nhận nếu pass auto validation, không có bước human review.

## Vai trò trong project

Milestone này tạo:

- gold labels để đánh giá extraction.
- pattern examples cho few-shot.
- dữ liệu để phân tích phân bố event type.
- relevance/evidence hints cho retrieval evaluation.

## Input

```text
data/processed/articles_clean.jsonl
docs/schema/event-schema.md
```

## Output

```text
data/labels/events_ai_generated.jsonl
data/labels/events_gold.jsonl
data/labels/events_rejected.jsonl
data/db/finevent_vn.sqlite
reports/data/labeling_summary.md
```

## Công nghệ

- Teacher LLM mạnh để sinh nhãn.
- Pydantic hoặc JSON Schema để validate.
- SQLite bảng `events_gold`.
- JSONL để lưu raw teacher output và validated gold.
- Repair prompt để sửa lỗi format/schema.

## Nguyên tắc gán nhãn

### Nhãn document

Mỗi bài có:

- `HAS_EVENT`: có ít nhất một sự kiện doanh nghiệp cụ thể.
- `NO_EVENT`: chỉ là phân tích chung, tin giá, nhận định thị trường, hoặc không có hành động doanh nghiệp rõ.

### Nhãn event

Nếu `HAS_EVENT`, mỗi event cần:

- `ticker`.
- `company_name`.
- `event_type`.
- `event_subtype` nếu đủ bằng chứng.
- `event_summary`.
- `event_arguments`.
- `impact_sentiment`.
- `evidence_span`.
- `confidence`.

Schema chỉ dùng chiều hướng tác động qua `impact_sentiment`.

### Evidence-first labeling

Teacher LLM chỉ được gán field nếu có bằng chứng trong bài. Field nào không có bằng chứng thì bỏ hoặc để `null`.

## Cách triển khai chi tiết

### Bước 1: Tạo prompt teacher

Prompt gồm:

1. Vai trò: chuyên gia trích xuất sự kiện doanh nghiệp.
2. Schema rút gọn.
3. Taxonomy event type/subtype.
4. Quy tắc `NO_EVENT`.
5. Quy tắc evidence span.
6. Bài báo input.

### Bước 2: Sinh nhãn lần đầu

Lưu mọi raw output vào `events_ai_generated.jsonl`, kể cả output lỗi.

Không ghi trực tiếp vào `events_gold.jsonl` trước khi validate.

### Bước 3: Auto validation

Kiểm tra:

- JSON parse được.
- Enum hợp lệ.
- `document_label` và `events` nhất quán.
- `event_subtype` hợp lệ với `event_type`.
- `evidence_span` xuất hiện trong text hoặc gần khớp.
- `event_arguments` là object.

### Bước 4: AI repair

Nếu lỗi format/schema, gọi repair prompt:

- chỉ sửa JSON.
- không thêm thông tin mới.
- không tự bịa evidence.
- nếu evidence sai, chọn lại từ bài gốc.

### Bước 5: Acceptance policy

Nếu output pass validation sau lần đầu hoặc sau repair:

- ghi vào `events_gold.jsonl`.
- ghi SQLite `events_gold`.

Nếu fail sau số lần retry:

- ghi vào `events_rejected.jsonl`.
- không dùng để evaluation.

## Kiểm thử

- Test validator với output hợp lệ.
- Test validator reject enum sai.
- Test validator reject event không evidence.
- Test repair không thêm field ngoài schema.

## Metrics

| Metric | Ý nghĩa |
| --- | --- |
| AI label count | Số bài đã gọi teacher |
| Gold pass count | Số bài pass validation |
| Auto validation pass rate | pass / total |
| Repair rate | số output cần repair |
| Rejection rate | số output fail sau retry |
| Event type coverage | số mẫu theo event type |
| NO_EVENT ratio | tỷ lệ bài không event |

## Done Criteria

- Có ít nhất 60 bài pass auto validation.
- Có ít nhất 6 event type chính.
- Có cả `HAS_EVENT` và `NO_EVENT`.
- Có `labeling_summary.md`.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Teacher bịa ticker | Cross-check dictionary, hạ confidence hoặc reject |
| Evidence không nằm trong bài | Repair chọn lại evidence hoặc reject event |
| Taxonomy quá chi tiết | Cho phép subtype null nếu thiếu bằng chứng |
| Dữ liệu lệch class | Crawl bổ sung theo event type thiếu |
