# 03 - Workflow Runner

## Implementation Update - Milestone Graph Composer

Trang Runs hiện dùng React Flow graph composer để chọn node M00-M08 theo dependency từ backend catalog. Tắt node sẽ tắt downstream node phụ thuộc, config nằm trong drawer/modal, run button mở confirm modal và UI không còn hiển thị raw payload review. Chi tiết implementation frontend nằm trong [13-milestone-graph-composer.md](13-milestone-graph-composer.md).

## Mục Tiêu

Workflow Runner là màn hình cho phép bấm chạy từng milestone hoặc workflow lớn.
Nó phải đủ rõ để người dùng biết sẽ chạy gì, dùng input nào, output nằm ở đâu và
đang chạy đến bước nào.

## Preset Workflows

### 1. Full M00-M08

Chạy toàn bộ pipeline end-to-end:

1. DB healthcheck.
2. Apply migrations.
3. Verify pgvector.
4. Ingest/clean articles.
5. Sync articles to PostgreSQL.
6. Teacher labeling.
7. Sync gold labels.
8. RAG preparation.
9. Sync chunks/embeddings.
10. Retrieval comparison.
11. Pattern library build.
12. Sync patterns.
13. Student 8B batch extraction.
14. Sync extraction runs.
15. Evaluation/report generation.

Output chính:

- `data/processed/articles_clean.jsonl`
- `data/labels/events_gold.jsonl`
- `data/retrieval/chunk_embeddings.jsonl`
- `data/patterns/patterns.jsonl`
- `data/extraction/student_predictions.jsonl`
- `reports/evaluation/report_index.md`

### 2. Data Collection + Cleaning + DB Sync

Chạy phần dữ liệu:

- crawl/download articles;
- parse HTML;
- clean text;
- extract metadata hints;
- sync PostgreSQL.

Khi dùng:

- cần thêm dữ liệu mới;
- cần kiểm tra crawler/parser;
- cần refresh bài báo trong DB.

### 3. RAG Preparation + Embedding

Chạy:

- structure-aware chunking;
- BM25 index;
- embedding API;
- vector artifact;
- pgvector sync.

Khi dùng:

- thay đổi chunking;
- thay embedding model;
- thêm corpus mới;
- muốn rebuild retrieval index.

### 4. Teacher Labeling

Chạy:

- teacher prompt;
- parse output;
- auto validation;
- accept AI labels as gold;
- sync DB.

Khi dùng:

- có bài mới chưa có gold label;
- thay teacher prompt;
- thay schema/taxonomy.

Không có human review trong workflow hiện tại theo quyết định của project.

### 5. Retrieval Evaluation

Chạy:

- BM25 only;
- dense only;
- hybrid;
- metadata-aware hybrid;
- rule-aware rerank;
- LLM reasoning rerank nếu bật.

Output:

- `reports/evaluation/retrieval_metrics.csv`
- `reports/evaluation/retrieval_error_analysis.md`

### 6. Pattern Library Build

Chạy:

- build patterns từ gold labels;
- validate pattern;
- embed patterns;
- sync pattern DB.

Output:

- `data/patterns/patterns.jsonl`
- `data/patterns/pattern_embeddings.jsonl`
- `reports/evaluation/pattern_library_summary.md`

### 7. Student 8B Batch Extraction

Chạy:

- retrieval;
- pattern selection;
- prompt budgeting;
- student 8B extraction;
- validation;
- verification;
- sync PostgreSQL;
- write prediction JSONL.

Output:

- `data/extraction/student_predictions.jsonl`
- `runs/extraction/*`

### 8. Final Evaluation And Reports

Chạy:

- compare predictions vs gold labels;
- aggregate metrics;
- write CSV/JSONL;
- write Markdown reports.

Output:

- `reports/evaluation/report_index.md`
- `reports/evaluation/eval_summary.md`
- `reports/evaluation/extraction_batch_summary.md`
- `reports/evaluation/verification_summary.md`
- `reports/evaluation/schema_error_summary.md`
- `reports/evaluation/improvement_recommendations.md`

## Controls Trên UI

Implementation hiện tại dùng graph workspace:

- React Flow graph M00-M08;
- node selected/available/blocked;
- edge label từ backend catalog;
- tooltip mô tả node;
- settings button trên selected node có config;
- settings drawer để cấu hình nhiều selected nodes;
- `Run workflow` button mở confirm modal;
- floating action mở run vừa tạo.

## Config Form

Form hiện tại được sinh từ `fields` trong `GET /admin/workflows/catalog`, không còn textarea JSON thủ công.

Field type:

| Type | Control |
| --- | --- |
| `text` | Text input |
| `number` | Stepper + numeric input |
| `select` | Select |
| `checkbox` | Toggle switch |
| `multi-select` | Pill buttons |

Các field vận hành chính:

| Field | Mặc định | Ghi chú |
| --- | --- | --- |
| `max_articles` | 25 hoặc empty | Giới hạn số bài cho test |
| `embedding_provider` | `hash` | Provider mặc định cho local/dev |
| `embedding_dimension` | 128 | Dimension mặc định trong node spec hiện tại |
| `student_provider` | `deterministic` | Có thể đổi sang `env` nếu endpoint model đã cấu hình |
| `retrieval_config` | `metadata_aware_hybrid` | Config tốt nhất hiện tại |
| `pattern_count` | 3 | Few-shot patterns |
| `max_contexts` | 5 | Context cho extraction |
| `limit` | 10 | Số bài chạy cho M06 |
| `offset` | 0 | Offset batch M06 |
| `sync_postgres` | true | Lưu kết quả vào DB |

Field có `configurable=false` vẫn là một phần backend catalog để UI hiểu contract, nhưng drawer cấu hình nhanh sẽ ẩn các field này.

## Run Lifecycle

```text
created -> queued -> running -> success
                       ├── failed
                       └── canceled
```

Khi bấm `Run`:

1. Frontend gọi `POST /admin/runs`.
2. Backend tạo `PipelineRun`.
3. Backend tạo danh sách `PipelineStep`.
4. Job runner bắt đầu chạy step đầu tiên.
5. Frontend redirect sang `/admin/runs/{run_id}`.
6. UI subscribe SSE logs.
7. Sau mỗi step, artifact/report link được cập nhật.

## Retry Và Cancel

Implementation hiện tại cần:

- cancel running run;
- xem run detail sau khi tạo run;
- xem live logs và artifacts.

Retry whole run hoặc retry from failed step chưa có API/UI ở thời điểm hiện tại.

## Failure UI

Khi step fail:

- timeline tô đỏ step lỗi;
- live log tự scroll đến dòng lỗi;
- hiển thị exit code;
- hiển thị command đã chạy;
- hiển thị stderr cuối cùng;
- hiển thị artifact đã sinh trước khi lỗi;
- gợi ý mở runbook/report liên quan.
