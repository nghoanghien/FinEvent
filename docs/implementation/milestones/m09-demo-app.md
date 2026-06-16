# M9: Demo App

## Mục tiêu

Dựng ứng dụng demo cơ bản để người xem nhập URL/text bài báo và thấy hệ thống trích xuất bảng sự kiện có evidence.

## Input

- URL bài báo.
- Hoặc text bài báo do user paste.

## Output

- Bảng sự kiện.
- Evidence span.
- Retrieval contexts.
- Selected patterns.
- Verification report.
- Export JSON/CSV.

## Công nghệ

- Next.js + TypeScript.
- FastAPI backend.
- LangGraph workflow từ M6 chạy ở backend.
- PostgreSQL + pgvector.
- Tailwind CSS hoặc shadcn/ui nếu muốn dựng UI nhanh.

## Cách triển khai chi tiết

### Bước 1: Tạo UI input

Hai chế độ:

- URL mode.
- Text mode.

User có thể chọn config:

- retrieval strategy.
- student model.
- pattern count.
- bật/tắt verification nếu cần demo ablation.

### Bước 2: Article preview

Hiển thị:

- title.
- source URL.
- published date.
- ticker/company hints.
- text preview.

### Bước 3: Retrieval trace

Bảng context:

- rank.
- source.
- ticker.
- BM25 score.
- vector score.
- rerank score.
- excerpt.

Nếu dùng LLM reasoning rerank, hiển thị reasoning summary.

### Bước 4: Pattern examples

Hiển thị:

- pattern id.
- event type/subtype.
- similarity.
- evidence.
- output example rút gọn.

### Bước 5: Event table

Bảng:

- ticker.
- company.
- event type.
- subtype.
- summary.
- impact sentiment.
- confidence.
- evidence.

### Bước 6: Verification report

Hiển thị:

- schema valid.
- evidence coverage.
- unsupported fields.
- dropped events.
- repair attempts.
- warnings.

### Bước 7: Export

Cho tải:

- final JSON.
- CSV event table.
- run trace nếu cần debug.

## Kiểm thử

- Demo bài `HAS_EVENT`.
- Demo bài `NO_EVENT`.
- URL lỗi không crash.
- LLM timeout có thông báo.
- JSON invalid vẫn hiển thị diagnostic.

## Metrics hiển thị trong app

- retrieval latency.
- LLM latency.
- verification latency.
- total latency.
- number of events.
- average confidence.
- evidence coverage.

## Done Criteria

- Chạy được `pnpm dev` hoặc `npm run dev` trong thư mục `frontend/`.
- Frontend gọi được FastAPI endpoint `/extract`.
- User nhập bài và thấy kết quả.
- Có ít nhất 2 case demo.
- UI không crash khi workflow lỗi.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Frontend chứa logic quá nhiều | Core logic ở backend, frontend chỉ gọi FastAPI |
| Output khó hiểu | Hiển thị theo step: retrieval -> pattern -> extraction -> verification |
| Demo chậm | Cache retrieval/index/model response nếu phù hợp |
