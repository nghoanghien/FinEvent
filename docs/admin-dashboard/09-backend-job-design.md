# 09 - Backend Job Design

## Mục Tiêu

Backend job runner cho phép UI bấm chạy workflow mà vẫn tận dụng CLI hiện có.
V1 không cần Celery ngay; dùng Python subprocess là đủ nếu thiết kế log/run state
rõ ràng.

## Nguyên Tắc

- UI không chạy command trực tiếp.
- Backend là nơi tạo run và quản lý process.
- Mỗi workflow gồm nhiều step.
- Mỗi step map sang một CLI command.
- stdout/stderr được stream và lưu lại.
- Artifact path được ghi vào run summary.
- Nếu một step fail, run dừng và ghi lỗi.

## Data Model Đề Xuất

### `admin_pipeline_runs`

| Field | Type | Mô tả |
| --- | --- | --- |
| run_id | text | Primary key |
| workflow_name | text | Tên preset |
| status | text | queued/running/success/failed/canceled |
| config_json | jsonb | Config UI gửi |
| started_at | timestamptz | Start time |
| finished_at | timestamptz | End time |
| current_step_id | text | Step hiện tại |
| summary_json | jsonb | Tổng kết |
| error_message | text | Lỗi cuối |

### `admin_pipeline_steps`

| Field | Type | Mô tả |
| --- | --- | --- |
| step_id | text | Primary key |
| run_id | text | FK |
| milestone | text | M00-M08 |
| name | text | Tên step |
| command | text | Command đã chạy |
| status | text | queued/running/success/failed/canceled |
| exit_code | int | Exit code |
| started_at | timestamptz | Start time |
| finished_at | timestamptz | End time |
| artifact_paths | jsonb | Files sinh ra |
| error_message | text | Lỗi |

### `admin_pipeline_log_events`

| Field | Type | Mô tả |
| --- | --- | --- |
| id | bigserial | Primary key |
| run_id | text | FK |
| step_id | text | FK |
| timestamp | timestamptz | Time |
| level | text | INFO/WARN/ERROR |
| source | text | stdout/stderr/system |
| message | text | Log line |

V1 có thể lưu logs vào file trước, DB sau. Nhưng API nên giữ shape như trên để
sau này nâng cấp không đổi frontend nhiều.

## Command Mapping

Workflow runner map preset sang commands.

Ví dụ Student 8B batch extraction:

```text
python -m finevent.extraction run-batch
  --student-provider env
  --sync-postgres
  --retrieval-query-embedding-provider direct_http
  --retrieval-query-embedding-dimension 1024
  --pattern-query-embedding-provider direct_http
  --pattern-query-embedding-dimension 1024
  --output-path data/extraction/student_predictions.jsonl
```

Evaluation:

```text
python -m finevent.evaluation run
  --predictions-path data/extraction/student_predictions.jsonl
  --ignore-runs-dir
  --default-config-name m06_online_extraction
```

## Process Handling

Backend cần:

- spawn subprocess;
- đọc stdout/stderr line by line;
- ghi log event;
- stream SSE;
- detect exit code;
- update step status;
- update run status.

Cancel:

- gửi terminate;
- nếu timeout thì kill;
- status `canceled`;
- giữ logs đã có.

## Artifact Detection

Mỗi step có expected artifacts:

| Step | Artifacts |
| --- | --- |
| ingestion | `data/processed/articles_clean.jsonl`, `reports/data/data_quality_summary.md` |
| labeling | `data/labels/events_gold.jsonl`, `reports/data/labeling_summary.md` |
| rag_prepare | `data/processed/chunks.jsonl`, `data/retrieval/chunk_embeddings.jsonl` |
| retrieval_eval | `reports/evaluation/retrieval_metrics.csv` |
| patterns | `data/patterns/patterns.jsonl`, `reports/evaluation/pattern_library_summary.md` |
| extraction_batch | `data/extraction/student_predictions.jsonl`, `runs/extraction/*` |
| evaluation | `reports/evaluation/report_index.md` |

Sau step success, backend kiểm tra path tồn tại và ghi vào artifact list.

## V1 Vs Long-Term

V1:

- subprocess;
- one process per run;
- in-memory process registry;
- logs file + optional DB metadata.

Long-term:

- Celery/RQ + Redis;
- separate worker process;
- retry policy;
- scheduled jobs;
- notification.

Không nên dùng Celery ngay nếu mục tiêu hiện tại là dashboard nội bộ và demo.

