# 11 - Testing And Acceptance

## Mục Tiêu Kiểm Thử

Đảm bảo Admin Dashboard không chỉ nhìn đẹp mà thật sự giúp vận hành pipeline:

- chạy được workflow;
- stream được log;
- đọc được DB;
- xem được report;
- xem được structured output;
- xử lý lỗi rõ ràng.

## Test Backend API

### Health

- `GET /admin/health` trả status cho API, PostgreSQL, pgvector.
- Không trả API key hoặc secret.
- Nếu DB down, response vẫn JSON rõ ràng.

### Runs

- `POST /admin/runs` tạo run mới.
- `GET /admin/runs` list run vừa tạo.
- `GET /admin/runs/{run_id}` trả steps.
- Cancel run đang chạy đổi status sang `canceled`.
- Run fail lưu exit code và error message.

### Logs

- SSE stream nhận được log event.
- Khi process kết thúc, stream nhận `run_finished`.
- Reconnect không làm mất toàn bộ log vì có endpoint logs thường.

### Reports

- List được report files.
- Render được Markdown content.
- Parse được CSV thành rows.
- Parse được JSONL có pagination.
- Path traversal bị reject.

### Database Browser

- List articles có pagination.
- Search articles theo title/ticker.
- Detail article trả metadata và links.
- Embedding endpoint không trả full vector mặc định.

## Test Frontend

### Overview

- Hiển thị health cards.
- Hiển thị latest metrics.
- Link report index hoạt động.

### Workflow Runner

- Chọn workflow preset.
- Chỉnh config cơ bản.
- Bấm run tạo run mới.
- Sau khi tạo run redirect sang detail.

### Run Detail

- Timeline hiện các step.
- Live logs append từng dòng.
- Failed step hiển thị lỗi đỏ.
- Artifact links mở đúng viewer.

### Database

- Table load được dữ liệu.
- Search/filter hoạt động.
- Detail drawer mở đúng record.
- Copy ID hoạt động.

### Reports

- Markdown render đúng.
- CSV hiển thị table.
- JSONL hiển thị list/detail.
- Missing report có empty state.

### Outputs

- Event table hiển thị đúng events.
- Evidence span hiển thị.
- Arguments hiển thị key-value.
- Verification metrics hiển thị.
- Raw JSON copy được.

## Scenario Tests

### Scenario 1 - Chạy Evaluation Reports

1. Mở `/admin/runs`.
2. Chọn `Final Evaluation And Reports`.
3. Bấm run.
4. Xem live logs.
5. Run success.
6. Mở artifact `report_index.md`.
7. Xem metrics cards được refresh.

### Scenario 2 - Chạy Student 8B Batch

1. Chọn `Student 8B Batch Extraction`.
2. Set `limit=5` để test nhanh.
3. Bấm run.
4. Xem log từng article.
5. Mở output viewer.
6. Event table có dữ liệu hoặc `NO_EVENT` rõ ràng.

### Scenario 3 - Debug Lỗi Model

1. Cấu hình sai student endpoint trong env test.
2. Chạy extraction.
3. Run fail ở step extraction.
4. UI hiển thị stderr tail.
5. Timeline chỉ rõ step lỗi.
6. Report/artifact trước lỗi vẫn xem được.

### Scenario 4 - Xem DB

1. Mở Database > Articles.
2. Search một ticker.
3. Mở article detail.
4. Click related chunks.
5. Click latest extraction output nếu có.

## Acceptance Criteria V1

V1 đạt nếu:

- Next.js app chạy local.
- FastAPI admin endpoints chạy local.
- UI tạo được một run từ workflow preset.
- UI stream logs realtime.
- UI hiển thị run timeline.
- UI mở được ít nhất 5 report quan trọng.
- UI xem được articles từ DB.
- UI xem được extraction output dạng bảng.
- Khi workflow lỗi, UI không crash và hiển thị lỗi rõ.

## Manual QA Checklist

- Không có secret trong UI.
- Không có path traversal report.
- Không query toàn bộ table lớn không pagination.
- Không hiện vector full trong table.
- Không gọi model API từ frontend.
- Reload trang run detail vẫn xem được logs cũ.
- Report viewer refresh sau khi run evaluation xong.
- Output viewer xử lý `NO_EVENT` đẹp, không hiện bảng rỗng khó hiểu.

## Metrics Dashboard Checklist

Hiển thị tối thiểu:

- Event F1.
- Event type macro-F1.
- Slot-F1.
- JSON validity.
- Schema compliance.
- Groundedness.
- Retrieval Recall@5.
- Retrieval MRR.
- Retrieval nDCG@10.
- Top error code.

