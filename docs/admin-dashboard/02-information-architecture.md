# 02 - Information Architecture

## Layout Tổng Thể

Dashboard dùng layout hai vùng:

- Sidebar cố định bên trái để điều hướng.
- Main content bên phải hiển thị màn hình hiện tại.

```text
Admin Dashboard
├── Overview
├── Workflow Runner
├── Runs
│   └── Run Detail
├── Database
│   ├── Articles
│   ├── Chunks
│   ├── Gold Labels
│   ├── Patterns
│   ├── Extraction Runs
│   └── Ticker Dictionary
├── Reports
├── Outputs
└── Settings & Health
```

## Màn Hình Overview

Mục đích: cho biết trạng thái hệ thống trong 30 giây đầu.

Các block cần có:

- API health.
- PostgreSQL health.
- pgvector health.
- Model endpoints health.
- Số bài báo trong DB.
- Số chunks/embeddings.
- Số gold labels.
- Số patterns.
- Số extraction runs.
- Metrics mới nhất: Event F1, Type F1, Slot F1, Schema Valid, Groundedness.
- Run gần nhất và status.
- Link nhanh đến report index.

## Màn Hình Workflow Runner

Mục đích: bấm chạy pipeline mà không nhớ CLI.

Các phần:

- Chọn workflow preset.
- Chọn config cơ bản.
- Preview command/backend plan trước khi chạy.
- Nút `Start Run`.
- Nút `Dry Run` nếu backend hỗ trợ.
- Link sang run detail sau khi tạo run.

Preset nên có:

- Full M00-M08.
- Data collection + DB sync.
- RAG preparation + embedding.
- Teacher labeling.
- Retrieval evaluation.
- Pattern library build.
- Student 8B batch extraction.
- Final evaluation/report generation.

## Màn Hình Runs

Mục đích: xem lịch sử các lần chạy.

Bảng runs:

| Cột | Mô tả |
| --- | --- |
| Run ID | Mã run |
| Workflow | Tên workflow/preset |
| Status | queued/running/success/failed/canceled |
| Started | Thời gian bắt đầu |
| Duration | Thời gian chạy |
| Current Step | Step hiện tại hoặc step lỗi |
| Success Steps | Số step thành công |
| Failed Steps | Số step lỗi |
| Actions | Open, retry, cancel nếu đang chạy |

Filter:

- status;
- workflow name;
- date range;
- failed only;
- latest only.

## Màn Hình Run Detail

Mục đích: thay thế terminal cho một run cụ thể.

Các tab:

1. Timeline
2. Live Logs
3. Artifacts
4. Metrics
5. Errors
6. Raw JSON

Timeline hiển thị mỗi step:

- milestone;
- command;
- status;
- start/end time;
- duration;
- artifact output;
- error message nếu có.

## Màn Hình Database

Mục đích: xem dữ liệu vận hành.

Các tab:

- Articles.
- Chunks.
- Gold Labels.
- Patterns.
- Extraction Runs.
- Node Traces.
- Ticker Dictionary.

Mỗi tab cần:

- search;
- filters;
- pagination;
- table;
- detail drawer.

## Màn Hình Reports

Mục đích: mở report sau khi chạy xong.

Các loại viewer:

- Markdown viewer cho `.md`.
- CSV table viewer cho `.csv`.
- JSON viewer cho `.json`.
- JSONL table/detail viewer cho `.jsonl`.

Report quan trọng:

- `reports/evaluation/report_index.md`
- `reports/evaluation/eval_summary.md`
- `reports/evaluation/extraction_batch_summary.md`
- `reports/evaluation/verification_summary.md`
- `reports/evaluation/schema_error_summary.md`
- `reports/evaluation/improvement_recommendations.md`
- `reports/data/data_quality_summary.md`
- `reports/data/labeling_summary.md`
- `reports/data/rag_preparation_summary.md`

## Màn Hình Outputs

Mục đích: xem output của model không cần đọc JSON.

Các phần:

- chọn run hoặc article;
- bảng events;
- event detail drawer;
- evidence span;
- arguments;
- validation issues;
- verification report;
- raw model output;
- gold vs prediction comparison nếu có gold.

## Màn Hình Settings & Health

Mục đích: kiểm tra hệ thống sẵn sàng trước khi chạy.

Hiển thị:

- `.env` variables có tồn tại hay không, không hiện secret;
- database DSN masked;
- Docker/Postgres status;
- pgvector extension;
- teacher LLM API smoke status;
- student LLM API smoke status;
- embedding API smoke status;
- artifact paths tồn tại hay không.

