# 04 - Live Logs And Observability

## Mục Tiêu

Live Logs giúp người dùng biết pipeline đang làm gì theo thời gian thực, giống
cách Google Colab/Jupyter hiển thị output của từng cell. Đây là tính năng quan
trọng vì nhiều bước chạy lâu: crawl, teacher labeling, embedding, batch extraction.

## UX Yêu Cầu

Mỗi run detail có tab `Live Logs`.

UI cần:

- hiển thị log từng dòng;
- tự scroll theo dòng mới;
- có nút pause auto-scroll;
- filter theo level: info/warning/error/debug;
- filter theo step;
- search trong logs;
- copy log;
- download full log;
- clear view nhưng không xóa log thật;
- badge step hiện tại.

## Log Line Format

Mỗi dòng log nên được chuẩn hóa:

```json
{
  "timestamp": "2026-06-23T10:15:01+07:00",
  "run_id": "run_...",
  "step_id": "m03_rag_prepare",
  "milestone": "M03",
  "level": "INFO",
  "source": "stdout",
  "message": "embedding_count=573"
}
```

## Log Sources

| Source | Mô tả |
| --- | --- |
| `stdout` | Output thường từ CLI |
| `stderr` | Error/warning từ process |
| `system` | Backend job runner tự ghi |
| `metric` | Progress counters |
| `artifact` | Artifact mới được sinh |

## Realtime Protocol

V1 dùng Server-Sent Events.

Endpoint:

```text
GET /admin/runs/{run_id}/logs/stream
```

Event types:

```text
event: log
event: step_started
event: step_finished
event: artifact_created
event: run_finished
event: heartbeat
```

Ưu điểm SSE:

- dễ implement với FastAPI;
- browser hỗ trợ sẵn `EventSource`;
- phù hợp stream một chiều từ backend đến UI;
- đủ cho use case xem log.

WebSocket chỉ cần khi:

- cần terminal interactive;
- cần gửi control message realtime phức tạp;
- cần multi-client collaboration.

## Step Timeline

Timeline phải tách khỏi logs nhưng đồng bộ theo logs.

Mỗi step hiển thị:

- name;
- command summary;
- status;
- duration;
- log count;
- warning count;
- error count;
- artifact links.

Status color:

| Status | UI |
| --- | --- |
| queued | gray |
| running | blue + spinner |
| success | green |
| failed | red |
| canceled | yellow |

## Progress Counters

Một số step nên parse progress:

| Step | Counters |
| --- | --- |
| ingestion | articles downloaded, parsed, cleaned |
| labeling | labeled count, rejected count |
| embedding | chunks embedded, cache hits |
| retrieval eval | eval cases, configs |
| pattern build | patterns accepted/rejected |
| extraction batch | articles done/total, success/error |
| evaluation | article count, error count |

Nếu CLI chưa emit progress chi tiết, job runner vẫn hiển thị:

- started;
- command;
- stdout lines;
- completed/failed;
- duration.

## Error Handling

Khi process fail:

- backend ghi `step_failed`;
- lưu exit code;
- lưu stderr tail;
- UI hiện error panel;
- UI giữ full logs để debug;
- run không tự xóa artifact đã sinh trước đó.

## Log Retention

V1:

- lưu log file trong `runs/admin/{run_id}/logs/`;
- lưu metadata trong PostgreSQL;
- UI đọc từ file hoặc endpoint.

Nên giữ:

- stdout.log;
- stderr.log;
- events.jsonl;
- command.json;

