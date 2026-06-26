# 08 - API Contract

## Implementation Update - Runs Workflow

Runs API hiện đã có thêm `GET /admin/workflows/catalog` cho Milestone Graph Composer. Endpoint này trả `{ items, edge_labels }`; mỗi item là node spec M00-M08 với `depends_on`, `default_config`, `expected_artifacts` và `fields`. `POST /admin/runs` hỗ trợ `workflow_name = "milestone_graph"` với `config.selected_nodes`; frontend gửi thêm `node_configs` và config phẳng đã merge để backend build CLI args.

Endpoint retry chưa được implement trong API hiện tại; UI hiện hỗ trợ create, detail, logs, stream logs và cancel.

## Mục Tiêu

FastAPI backend cung cấp API cho Next.js admin dashboard. Frontend không gọi trực
tiếp CLI, không đọc DB trực tiếp và không chứa core NLP logic.

API hiện tại mới có health và ticker dictionary. Admin Dashboard cần thêm nhóm
endpoint mới dưới prefix `/admin`.

## Nhóm Health

### `GET /health`

Đã có.

### `GET /admin/health`

Response:

```json
{
  "api": "ok",
  "postgres": "ok",
  "pgvector": "ok",
  "teacher_llm": "unknown",
  "student_llm": "unknown",
  "embedding": "unknown",
  "artifacts": {
    "reports_dir": true,
    "data_dir": true
  }
}
```

Không trả secret.

## Nhóm Runs

### `GET /admin/workflows/catalog`

Response rút gọn:

```json
{
  "items": [
    {
      "id": "m00_runtime",
      "milestone": "M00",
      "title": "Runtime and database",
      "depends_on": [],
      "default_config": {},
      "expected_artifacts": [],
      "fields": []
    }
  ],
  "edge_labels": {
    "m00_runtime->m01_ingestion": "Db Connection"
  }
}
```

### `GET /admin/runs`

Query:

- `status`
- `workflow_name`
- `limit`
- `offset`

Response:

```json
{
  "items": [
    {
      "run_id": "admin_run_...",
      "workflow_name": "student_batch_extraction",
      "status": "success",
      "started_at": "...",
      "finished_at": "...",
      "duration_ms": 355700,
      "current_step": "evaluation",
      "success_step_count": 8,
      "failed_step_count": 0
    }
  ],
  "total": 1
}
```

### `POST /admin/runs`

Body:

```json
{
  "workflow_name": "milestone_graph",
  "config": {
    "selected_nodes": ["m00_runtime", "m01_ingestion", "m06_extraction"],
    "node_configs": {
      "m06_extraction": {
        "limit": 10,
        "sources": ["cafef"]
      }
    },
    "limit": 10,
    "sources": ["cafef"]
  }
}
```

Response:

```json
{
  "run_id": "admin_run_...",
  "status": "queued",
  "detail_url": "/admin/runs/admin_run_..."
}
```

### `GET /admin/runs/{run_id}`

Trả metadata run, steps, artifacts, summary.

### `POST /admin/runs/{run_id}/cancel`

Cancel process nếu đang chạy.

### Future: `POST /admin/runs/{run_id}/retry`

Chưa có trong implementation hiện tại.

## Nhóm Logs

### `GET /admin/runs/{run_id}/logs`

Query:

- `step_id`
- `level`
- `limit`
- `offset`

### `GET /admin/runs/{run_id}/logs/stream`

SSE stream.

Event payload:

```json
{
  "timestamp": "...",
  "run_id": "...",
  "step_id": "m06_student_batch",
  "level": "INFO",
  "source": "stdout",
  "message": "success_count=32"
}
```

## Nhóm Database Browser

### `GET /admin/db/{entity}`

Entity:

- articles
- chunks
- embeddings
- gold-labels
- patterns
- extraction-runs
- node-traces
- tickers

Query:

- `query`
- `limit`
- `offset`
- entity-specific filters.

### `GET /admin/db/{entity}/{id}`

Trả detail record.

## Nhóm Reports

### `GET /admin/reports`

Trả danh sách report files.

### `GET /admin/reports/content`

Query:

- `path`

Trả text content cho Markdown/raw JSON.

### `GET /admin/reports/table`

Parse CSV thành rows/columns.

### `GET /admin/reports/jsonl`

Parse JSONL có pagination.

## Nhóm Outputs

### `GET /admin/outputs`

List extraction outputs theo article/run.

### `GET /admin/outputs/{run_id}`

Trả structured output:

```json
{
  "article": {},
  "prediction": {},
  "events": [],
  "retrieval_trace": [],
  "selected_patterns": [],
  "validation_issues": [],
  "verification_report": {},
  "hallucination_metrics": {}
}
```

### `GET /admin/outputs/by-article/{article_id}`

Trả latest extraction output cho article.

## Error Format

Mọi API lỗi nên trả:

```json
{
  "error_code": "REPORT_NOT_FOUND",
  "message": "Report path does not exist",
  "details": {
    "path": "reports/evaluation/..."
  }
}
```

## Security V1

- Không expose `.env`.
- Không trả API key.
- Mask DSN.
- Chỉ cho đọc file trong allowlist: `reports/`, `data/`, `runs/`.
- Không cho path traversal như `../../.env`.
