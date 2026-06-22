# 03 - Backend Job Runner

## Vai trò

Job runner cho phép admin dashboard bấm chạy workflow mà không gọi CLI trực tiếp
từ frontend. Backend tạo run, spawn subprocess, lưu log và cập nhật trạng thái.

## Workflow Whitelist

Frontend chỉ được gửi `workflow_name` thuộc allowlist:

| Workflow | Step |
| --- | --- |
| `evaluation` | M08 evaluation/report/charts |
| `student_batch_extraction` | M06 student batch extraction |
| `student_batch_with_evaluation` | M06 extraction rồi M08 evaluation |

API không nhận command tự do. Điều này tránh lỗi bảo mật kiểu remote command
execution.

## Queue Và Concurrency

Runner v1 dùng queue nội bộ:

```text
queued -> running -> success / failed / canceled / interrupted
```

Env điều khiển:

```text
FINEVENT_MAX_CONCURRENT_RUNS=1
FINEVENT_MAX_QUEUE_SIZE=20
```

Ý nghĩa:

- `FINEVENT_MAX_CONCURRENT_RUNS`: số subprocess workflow được chạy cùng lúc.
- `FINEVENT_MAX_QUEUE_SIZE`: số run được phép chờ trong queue.

Nếu queue đầy, `POST /admin/runs` trả HTTP `429` với `RUN_QUEUE_FULL`.

## Run State

Mỗi run được lưu ở:

```text
runs/admin/{run_id}/
  run.json
  logs/
    events.jsonl
```

`run.json` chứa:

- `run_id`;
- `workflow_name`;
- `status`;
- `config`;
- `steps`;
- `created_at`, `started_at`, `finished_at`;
- `current_step_id`;
- `summary`;
- `error_message`.

## Log Format

Mỗi dòng trong `events.jsonl`:

```json
{
  "timestamp": "2026-06-23T...",
  "run_id": "admin_run_...",
  "step_id": "m08_evaluation",
  "level": "INFO",
  "source": "stdout",
  "message": "..."
}
```

UI có thể:

- gọi `GET /admin/runs/{run_id}/logs` để load lịch sử;
- gọi `GET /admin/runs/{run_id}/logs/stream` để stream live logs bằng SSE.

## Artifact Tracking

Sau mỗi step thành công, runner kiểm tra expected artifacts:

| Step | Artifacts |
| --- | --- |
| M06 extraction | `data/extraction/student_predictions.jsonl` hoặc `output_path` trong config |
| M08 evaluation | `reports/evaluation/report_index.md`, `charts_summary.md`, `academic_charts_summary.md` |

Các path tồn tại được ghi vào `artifact_paths` của step.

## Cancel

`POST /admin/runs/{run_id}/cancel` terminate process đang chạy. Nếu run chưa chạy
xong, các step còn lại được đánh dấu `canceled`.

Nếu run vẫn đang `queued`, API xóa run khỏi queue và đánh dấu `canceled` mà không
spawn subprocess.

## Startup Reconciliation

Khi FastAPI startup, runner scan:

```text
runs/admin/*/run.json
```

Nếu thấy run có status `queued` hoặc `running`, API đánh dấu run đó thành
`interrupted` và ghi log:

```text
Server restarted before this run completed.
```

Thiết kế này tránh UI bị kẹt trạng thái `running` sau khi server restart. Với
subprocess runner nội bộ, backend không cố reattach process cũ vì điều đó không
đáng tin cậy ở V1.

## Giới hạn v1

- Runner dùng Python thread + subprocess trong cùng FastAPI process.
- Phù hợp cho demo, local dashboard và workflow nội bộ.
- Khi chạy production nhiều người dùng, có thể nâng cấp sang worker riêng như RQ,
  Celery, Dramatiq hoặc Prefect.

Vì project hiện tại ưu tiên demo và quan sát workflow, cách này đủ gọn mà vẫn giữ
được API shape ổn định cho frontend.
