# 05 - Milestone Graph Runner API

## Mục Tiêu

Milestone Graph Runner là workflow API cho trang Runs của admin dashboard. UI chọn các node M00-M08 trên graph, backend validate dependency, build danh sách `WorkflowStep`, rồi job runner chạy từng subprocess theo allowlist.

Workflow chính:

```text
workflow_name = "milestone_graph"
```

Backend vẫn giữ các workflow legacy để tương thích:

```text
evaluation
student_batch_extraction
student_batch_with_evaluation
```

## Code Map

```text
src/finevent/api/
  admin_workflows.py
  admin_runs.py
  job_runner.py
  main.py
  workflow_registry/
    __init__.py
    catalog.py
    config_helpers.py
    types.py
    nodes/
      __init__.py
      m00_runtime.py
      m01_ingestion.py
      m02_labeling.py
      m03_rag.py
      m04_retrieval.py
      m05_patterns.py
      m06_extraction.py
      m07_verification.py
      m08_evaluation.py
```

Vai trò chính:

| Module | Vai trò |
| --- | --- |
| `admin_workflows.py` | Expose `GET /admin/workflows/catalog` cho UI |
| `admin_runs.py` | Nhận `POST /admin/runs`, map lỗi workflow/config sang API error |
| `job_runner.py` | Tạo run id, gọi registry build step, queue subprocess, ghi run/log |
| `workflow_registry/catalog.py` | Registry service: catalog, edge label, dependency validation, legacy workflow bridge |
| `workflow_registry/types.py` | Dataclass contract cho node, field, step, build context |
| `workflow_registry/nodes/*.py` | Node spec và command builder riêng cho từng milestone |

## Public Endpoints

### GET /admin/workflows/catalog

Trả catalog node graph để frontend hydrate graph, form config và edge labels.

Response shape hiện tại:

```json
{
  "items": [
    {
      "id": "m06_extraction",
      "milestone": "M06",
      "title": "Student extraction",
      "description": "Run student model extraction over selected clean articles.",
      "depends_on": ["m03_rag", "m05_patterns"],
      "default_config": {
        "limit": 10,
        "offset": 0,
        "sources": ["cafef"],
        "output_path": "data/extraction/student_predictions.jsonl"
      },
      "expected_artifacts": ["data/extraction/student_predictions.jsonl"],
      "fields": [
        {
          "key": "sources",
          "label": "Nguồn bài",
          "type": "multi-select",
          "options": [{ "value": "cafef", "label": "CafeF" }],
          "configurable": true
        }
      ]
    }
  ],
  "edge_labels": {
    "m05_patterns->m06_extraction": "Discovery Patterns"
  }
}
```

Không có wrapper `workflows` trong response này. Frontend lấy trực tiếp `items` để dựng node và lấy `edge_labels` để hiển thị label trên cạnh graph.

### POST /admin/runs

Tạo run mới.

Request tối thiểu cho graph workflow:

```json
{
  "workflow_name": "milestone_graph",
  "config": {
    "selected_nodes": [
      "m00_runtime",
      "m01_ingestion",
      "m02_labeling",
      "m03_rag",
      "m04_retrieval",
      "m05_patterns",
      "m06_extraction",
      "m07_verification",
      "m08_evaluation"
    ],
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

Quan trọng: command builder hiện đọc config phẳng ở `config`, ví dụ `limit`, `sources`, `output_path`. Frontend đang gửi cả config phẳng đã merge và `node_configs`; `node_configs` hữu ích để trace/debug UI, còn config phẳng là phần backend dùng để build CLI args.

Response thành công:

```json
{
  "run": {
    "run_id": "admin_run_20260624_...",
    "workflow_name": "milestone_graph",
    "status": "queued",
    "steps": []
  },
  "run_id": "admin_run_20260624_...",
  "status": "queued",
  "detail_url": "/admin/runs/admin_run_20260624_..."
}
```

## Registry Pattern

Mỗi node là một `WorkflowNodeSpec`:

```text
id
milestone
title
description
depends_on
default_config
expected_artifacts
fields
build_steps(context)
```

Mỗi config field là `WorkflowFieldSpec`:

```text
key
label
type              # text | number | select | checkbox | multi-select
description
min/max/step
options
configurable
```

`WorkflowNodeSpec.to_catalog_item()` serialize node spec thành JSON cho frontend. `build_steps(context)` tạo một hoặc nhiều `WorkflowStep`, mỗi step gồm `step_id`, `milestone`, `name`, `command`, `expected_artifacts`.

## Graph Hiện Tại

| Node | Phụ thuộc | Vai trò |
| --- | --- | --- |
| `m00_runtime` | none | Database healthcheck, migrations, pgvector verify |
| `m01_ingestion` | `m00_runtime` | Ingest/clean articles và sync PostgreSQL |
| `m02_labeling` | `m01_ingestion` | Generate teacher prompts, call teacher, validate labels, sync labels |
| `m03_rag` | `m01_ingestion` | Chunk articles, build embeddings/BM25/vector artifacts, sync retrieval |
| `m04_retrieval` | `m02_labeling`, `m03_rag` | Evaluate retrieval/reranking against gold labels |
| `m05_patterns` | `m02_labeling`, `m03_rag` | Build pattern library, pattern embeddings, sync patterns |
| `m06_extraction` | `m03_rag`, `m05_patterns` | Run student batch extraction |
| `m07_verification` | `m06_extraction` | Bật verification trong M06 extraction |
| `m08_evaluation` | `m04_retrieval`, `m07_verification` | Generate evaluation reports/charts |

Edge labels hiện tại:

| Edge | Label |
| --- | --- |
| `m00_runtime->m01_ingestion` | Db Connection |
| `m01_ingestion->m02_labeling` | Clean Articles |
| `m01_ingestion->m03_rag` | Clean Articles |
| `m02_labeling->m04_retrieval` | Gold Labels |
| `m02_labeling->m05_patterns` | Gold Labels |
| `m03_rag->m04_retrieval` | Text Chunks |
| `m03_rag->m05_patterns` | Text Chunks |
| `m03_rag->m06_extraction` | RAG Index |
| `m05_patterns->m06_extraction` | Discovery Patterns |
| `m06_extraction->m07_verification` | Student Predictions |
| `m04_retrieval->m08_evaluation` | Retrieval Metrics |
| `m07_verification->m08_evaluation` | Verified Events |

## Command Mapping

| Node | Step id chính | Command/module chính |
| --- | --- | --- |
| `m00_runtime` | `m00_database_healthcheck`, `m00_apply_migrations`, `m00_verify_pgvector` | `python -m finevent.database.cli ...` |
| `m01_ingestion` | `m01_data_ingestion` | `python -m finevent.ingestion ...` |
| `m02_labeling` | `m02_generate_teacher_prompts`, `m02_teacher_labeling`, `m02_validate_labels`, `m02_sync_labels` | `python -m finevent.labeling ...` |
| `m03_rag` | `m03_rag_preparation`, `m03_sync_retrieval` | `python -m finevent.rag ...` |
| `m04_retrieval` | `m04_retrieval_evaluation` | `python -m finevent.retrieval compare ...` |
| `m05_patterns` | `m05_pattern_library`, `m05_sync_patterns` | `python -m finevent.patterns ...` |
| `m06_extraction` | `m06_student_batch_extraction` hoặc `m06_m07_extraction_verification` | `python -m finevent.extraction run-batch ...` |
| `m07_verification` | none | Modifier flag cho M06 |
| `m08_evaluation` | `m08_evaluation` | `python -m finevent.evaluation run ...` |

`m07_verification` không sinh subprocess riêng. Nếu M07 được chọn, M06 build step dùng tên `m06_m07_extraction_verification` và không thêm `--disable-verification`. Nếu M07 không được chọn, M06 command thêm `--disable-verification`.

## Config Theo Node

| Node | Config chính |
| --- | --- |
| `m01_ingestion` | `articles_path`, `max_articles`, `max_discovered_urls`, `min_text_chars`, `discover_download`, `sync_postgres` |
| `m02_labeling` | `max_articles`, `teacher_max_retries`, `generate_prompts`, `run_teacher`, `validate_labels`, `strict_validation`, `sync_postgres` |
| `m03_rag` | `embedding_provider`, `embedding_model`, `embedding_dimension`, `target_words`, `max_words`, `overlap_words`, `sync_postgres` |
| `m04_retrieval` | `embedding_provider`, `embedding_model`, `embedding_dimension`, `retrieval_metrics_path` |
| `m05_patterns` | `embedding_provider`, `embedding_model`, `embedding_dimension`, `sync_postgres` |
| `m06_extraction` | `sources`, `limit`, `offset`, `output_path`, `student_provider`, `embedding_provider`, `embedding_dimension`, `use_retrieval`, `use_patterns`, `sync_postgres` |
| `m07_verification` | none |
| `m08_evaluation` | `gold_path`, `evaluation_output_dir`, `skip_academic_figures` |

Field có `configurable=false` vẫn được trả trong catalog để UI biết default/contract, nhưng không nên xem là field vận hành thông thường.

## Source Filtering

M06 hỗ trợ lọc articles theo `sources`.

Khi config có `sources` và backend có `run_id`, registry tạo file:

```text
runs/admin/{run_id}/inputs/articles_filtered.jsonl
```

Luồng xử lý:

1. Đọc `articles_path`, mặc định `data/processed/articles_clean.jsonl`.
2. Parse từng dòng JSONL.
3. Giữ record có `record["source"]` nằm trong `sources`.
4. Ghi JSONL đã lọc vào thư mục run.
5. Build command `finevent.extraction run-batch --articles-path <filtered-file>`.

File data gốc không bị sửa.

## Validation Và Error Rules

| Trường hợp | HTTP/Error code | Ghi chú |
| --- | --- | --- |
| `workflow_name` không tồn tại | `UNKNOWN_WORKFLOW` | Message bắt đầu bằng `Unknown workflow_name` |
| Thiếu `config.selected_nodes` cho `milestone_graph` | `INVALID_WORKFLOW_CONFIG` | Registry raise `milestone_graph requires config.selected_nodes.` |
| Không có node hợp lệ nào được chọn | `INVALID_WORKFLOW_CONFIG` | Registry raise `Select at least one milestone node.` |
| Thiếu dependency | `INVALID_WORKFLOW_CONFIG` | Message dạng `M08 requires prerequisite node(s): M04, M07.` |
| Node được chọn nhưng không sinh step nào | `INVALID_WORKFLOW_CONFIG` | Ví dụ chỉ có node modifier không runnable |
| Queue đầy | `RUN_QUEUE_FULL` | HTTP 429 |
| Step subprocess fail | Run status `failed` | Xem `runs/admin/{run_id}/logs/events.jsonl` |

Backend sắp xếp `selected_nodes` theo thứ tự `WORKFLOW_NODES`, không theo thứ tự caller gửi lên.

## Run Lifecycle Và Files

```text
queued -> running -> success / failed / canceled / interrupted
```

File run:

```text
runs/admin/{run_id}/
  run.json
  logs/
    events.jsonl
  inputs/
    articles_filtered.jsonl  # chỉ có khi M06 source filter được dùng
```

Logs API:

```text
GET /admin/runs/{run_id}/logs
GET /admin/runs/{run_id}/logs/stream
```

## Cách Thêm Node Mới

1. Tạo file `src/finevent/api/workflow_registry/nodes/mXX_*.py`.
2. Khai báo `node_spec = WorkflowNodeSpec(...)`.
3. Implement `build_steps(context)` và chỉ build command từ allowlist code-side.
4. Import node spec vào `workflow_registry/nodes/__init__.py` và thêm vào `WORKFLOW_NODES`.
5. Thêm edge label vào `EDGE_LABELS` nếu UI cần label cạnh.
6. Cập nhật frontend `WorkflowNodeId`, `workflowNodeOrder`, `workflowNodePresentation`.
7. Cập nhật docs và test dependency/catalog.

Checklist backend:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m ruff check src/finevent/api tests/test_admin_api.py
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_admin_api.py
```

## Ghi Chú Bảo Trì

- Không nhận raw command từ frontend.
- Logic node nằm trong `workflow_registry/nodes/`, không nhồi thêm vào `job_runner.py`.
- `job_runner.py` chỉ quản lý run state, queue, subprocess, logs và artifacts.
- Frontend validate dependency để UX tốt hơn, nhưng backend validation mới là contract bắt buộc.
- Nếu đổi field key trong node spec, cần kiểm tra lại `workflow-composer/state.ts` vì frontend merge config phẳng dựa trên các key này.
