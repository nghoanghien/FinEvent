# 02 - Backend API Endpoints

## Authentication

Tất cả endpoint dưới `/admin/*` yêu cầu header:

```text
X-Admin-API-Key: <FINEVENT_ADMIN_API_KEY>
```

Ngoại lệ: `GET /health` là public health check tối giản.

## Health

### `GET /health`

Health check tối giản.

### `GET /admin/health`

Trả trạng thái API, PostgreSQL, pgvector, artifact dirs và việc cấu hình model env.
Không trả secret.

## Reports

### `GET /admin/reports`

Query:

- `kind`: lọc theo `markdown`, `csv`, `jsonl`, `svg`, `image`.
- `limit`, `offset`.

Response gồm `items`, `total`, `limit`, `offset`.

### `GET /admin/reports/content?path=...`

Đọc Markdown, JSON, JSONL, CSV, SVG, text. Với PNG/PDF, API trả file response.

Ví dụ:

```text
GET /admin/reports/content?path=reports/evaluation/academic_charts_summary.md
GET /admin/reports/content?path=reports/evaluation/figures_academic/final_quality_dashboard.png
```

### `GET /admin/reports/table?path=...`

Parse CSV thành:

```json
{
  "columns": ["config_name", "event_detection_f1"],
  "rows": [],
  "total": 0,
  "limit": 100,
  "offset": 0
}
```

### `GET /admin/reports/jsonl?path=...`

Parse JSONL có pagination và trả `parse_errors` nếu có dòng lỗi.

### `GET /admin/reports/charts`

Trả chart groups cho UI:

- lightweight SVG;
- dataset;
- retrieval;
- extraction;
- verification;
- final dashboard.

## Runs

### `GET /admin/workflows/catalog`

Trả catalog node graph backend đang hỗ trợ. Response hiện có `{ "items": [...], "edge_labels": { ... } }`; mỗi item gồm `id`, `milestone`, `title`, `description`, `depends_on`, `default_config`, `expected_artifacts`, `fields`. UI dùng endpoint này để dựng graph M00-M08, form config và label cạnh. Chi tiết contract nằm trong [05-milestone-graph-runner.md](05-milestone-graph-runner.md).

### `GET /admin/runs`

List workflow runs trong `runs/admin`.

Query:

- `status`;
- `workflow_name`;
- `limit`;
- `offset`.

### `POST /admin/runs`

Tạo workflow run mới.

```json
{
  "workflow_name": "evaluation",
  "config": {
    "gold_path": "data/labels/events_gold.jsonl",
    "runs_dir": "runs/extraction",
    "evaluation_output_dir": "reports/evaluation"
  }
}
```

Workflow được hỗ trợ:

- `milestone_graph`;
- `evaluation`;
- `student_batch_extraction`;
- `student_batch_with_evaluation`.

Với `milestone_graph`, `config` phải có `selected_nodes`. Frontend hiện gửi thêm `node_configs` và config phẳng đã merge; command builder backend đang đọc config phẳng.

Nếu queue đầy, API trả:

```json
{
  "error_code": "RUN_QUEUE_FULL",
  "message": "Admin run queue is full..."
}
```

### `GET /admin/runs/{run_id}`

Trả run metadata, steps, status, artifact paths.

Status hợp lệ:

```text
queued, running, success, failed, canceled, interrupted
```

### `POST /admin/runs/{run_id}/cancel`

Terminate process đang chạy và đánh dấu run là `canceled`.

### `GET /admin/runs/{run_id}/logs`

Đọc JSONL logs có pagination.

### `GET /admin/runs/{run_id}/logs/stream`

SSE stream để UI hiển thị log live.

## Database Browser

### `GET /admin/db/{entity}`

Entity allowlist:

- `articles`;
- `chunks`;
- `embeddings`;
- `gold-labels`;
- `gold-events`;
- `patterns`;
- `extraction-runs`;
- `node-traces`;
- `tickers`.

Query:

- `query`;
- `limit`;
- `offset`.

### `GET /admin/db/{entity}/{record_id}`

Trả detail record. Với embedding vector, API không trả toàn bộ vector, chỉ trả
`"<vector omitted>"` để tránh response quá lớn.

## Outputs

### `GET /admin/outputs`

Query:

- `article_id`;
- `source`: `auto`, `postgres`, `filesystem`;
- `limit`, `offset`.

`auto` ưu tiên PostgreSQL nếu có, sau đó đọc filesystem artifact.

### `GET /admin/outputs/{run_id}`

Trả structured output của một extraction run.

### `GET /admin/outputs/by-article/{article_id}`

Trả extraction output mới nhất theo `article_id`.
