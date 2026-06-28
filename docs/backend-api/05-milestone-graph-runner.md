# 05 - API Chạy Graph Milestone

Tài liệu này là contract backend cho trang Runs của admin dashboard. Graph runner
không nhận raw command từ frontend. UI chỉ gửi danh sách node được chọn và config
từng node; backend tự validate dependency rồi build danh sách `WorkflowStep` từ code
allowlist.

Workflow chính:

```text
milestone_graph
```

Các workflow legacy vẫn còn để tương thích:

```text
evaluation
student_batch_extraction
student_batch_with_evaluation
```

## Sơ Đồ Code

```text
src/finevent/api/
  admin_workflows.py
  admin_runs.py
  job_runner.py
  report_store.py
  main.py
  workflow_registry/
    catalog.py
    config_helpers.py
    types.py
    nodes/
      m00_runtime.py
      m01_ingestion.py
      m02_labeling.py
      m03_rag.py
      m04_retrieval.py
      m06_extraction.py
      m07_verification.py
      m08_evaluation.py
```

| Module | Vai trò |
| --- | --- |
| `admin_workflows.py` | Expose `GET /admin/workflows/catalog` |
| `admin_runs.py` | Nhận tạo/hủy run, đọc log và map lỗi workflow |
| `job_runner.py` | Tạo run id, queue subprocess, ghi run state, log và artifact |
| `report_store.py` | Lưu artifact trong `reports/...` vào PostgreSQL `workflow_reports` |
| `workflow_registry/catalog.py` | Quản lý thứ tự node, edge label, dependency validation và legacy bridge |
| `workflow_registry/nodes/*.py` | Khai báo field config và command builder cho từng node |

## Nguyên Tắc Thiết Kế

Graph runner được thiết kế như một lớp orchestration an toàn cho admin UI, không phải
một shell executor. Frontend chỉ được phép nói "chạy node nào" và "config của node là
gì"; backend mới là nơi quyết định command cụ thể.

Các nguyên tắc bắt buộc:

- Không nhận raw command từ frontend.
- Không để frontend tự quyết định dependency.
- Mọi command subprocess phải được build trong `workflow_registry/nodes/*.py`.
- Mỗi node phải mô tả rõ input, output, expected artifacts và field config.
- Config field cần có default để run có thể chạy lại được sau khi reload UI.
- Backend luôn validate lại, kể cả frontend đã validate.
- Artifact path mặc định phải nằm trong workspace, tránh path traversal.

Điểm quan trọng là graph runner không chỉ phục vụ UI hiện tại. Nó còn là contract để
sau này có thể thêm worker queue, run history, hoặc scheduler mà không đổi cách node
định nghĩa workflow.

## Registry Model

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

`fields` mô tả form config cho frontend. `default_config` mô tả giá trị runtime thật.
Hai phần này phải khớp nhau: field nào có thể cấu hình thì nên có default tương ứng,
còn field `configurable=false` vẫn có thể nằm trong `default_config` để command builder
dùng.

`build_steps(context)` nhận `BuildContext` gồm:

```text
python
config
selected_nodes
run_id
selected(node_id)
```

`selected(node_id)` dùng cho node modifier như M07. M07 không sinh subprocess riêng,
nhưng M06 cần biết M07 có được chọn không để quyết định có thêm
`--disable-verification` hay không.

Mỗi `WorkflowStep` gồm:

```text
step_id
milestone
name
command
expected_artifacts
```

`expected_artifacts` không chỉ để UI biết output nằm đâu. Job runner còn dùng danh
sách này để đăng ký report artifacts vào DB sau khi step chạy thành công.

## Endpoint

### `GET /admin/workflows/catalog`

Trả catalog để frontend dựng graph composer.

```json
{
  "items": [
    {
      "id": "m04_retrieval",
      "milestone": "M04",
      "title": "Online retrieval",
      "description": "Retrieve article contexts from chunk embeddings/BM25 and attach chunk-matched patterns.",
      "depends_on": ["m02_labeling", "m03_rag"],
      "default_config": {
        "retrieval_config": "metadata_aware_hybrid",
        "max_contexts": 10,
        "retrieval_results_path": "data/retrieval/online_contexts.jsonl"
      },
      "expected_artifacts": ["data/retrieval/online_contexts.jsonl"],
      "fields": []
    }
  ],
  "edge_labels": {
    "m04_retrieval->m06_extraction": "Retrieved Contexts"
  }
}
```

Response không có wrapper `workflows`. Frontend đọc trực tiếp `items` và dùng
`edge_labels` để hiển thị label trên cạnh graph.

### `POST /admin/runs`

Tạo admin run. Request tối thiểu cho graph workflow:

```json
{
  "workflow_name": "milestone_graph",
  "config": {
    "selected_nodes": ["m00_runtime", "m01_ingestion", "m02_labeling"],
    "node_configs": {
      "m01_ingestion": {
        "sources": ["cafef", "vietstock"],
        "discover_download": true
      }
    }
  }
}
```

Frontend vẫn gửi cả `node_configs` và config phẳng để tương thích. Backend ưu tiên
`node_configs.<node_id>` khi build command, rồi mới fallback sang config phẳng nếu
node không có config riêng. Cách này tránh đụng key, ví dụ M01 `sources` dùng cho
crawl còn M06 `sources` dùng để lọc clean articles.

## Config Merge

Config có hai tầng:

```json
{
  "selected_nodes": ["m00_runtime", "m01_ingestion"],
  "node_configs": {
    "m01_ingestion": {
      "sources": ["cafef"],
      "discover_download": true
    }
  },
  "sources": ["cafef"]
}
```

Backend xử lý theo thứ tự:

1. Lấy `node_configs.<node_id>` nếu có.
2. Nếu node không có config riêng, fallback sang config phẳng.
3. Command builder trong từng node đọc config bằng helper như `str_config`,
   `int_config`, `bool_config`.
4. Nếu thiếu key thì helper dùng default hard-coded trong node spec.

Cách này giữ tương thích với workflow legacy và tránh tình trạng key trùng nghĩa giữa
các node. Ví dụ `sources` ở M01 là nguồn crawl, còn `sources` ở M06 là filter clean
articles. Hai field cùng tên nhưng không có cùng vai trò runtime.

## Vòng Đời Run

Run đi qua các trạng thái:

```text
queued -> running -> success / failed / canceled / interrupted
```

Khi nhận `POST /admin/runs`, backend:

1. Validate workflow name.
2. Validate `selected_nodes`.
3. Sort node theo registry order.
4. Validate dependency.
5. Build danh sách `WorkflowStep`.
6. Ghi `runs/admin/{run_id}/run.json`.
7. Queue background job.
8. Ghi event log trong `runs/admin/{run_id}/logs/events.jsonl`.

Nếu subprocess fail, run dừng ở step đó và status thành `failed`. Backend không tự
retry step vì mỗi node có side effect khác nhau: M01 có thể crawl/download, M02 có thể
gọi teacher LLM, M03/M04 có thể ghi artifacts lớn. Retry nên là một lần run mới để
log và artifact rõ ràng.

## Artifact Và Report

Không phải artifact nào cũng được copy vào DB. Quy ước hiện tại:

- File data vận hành như `data/processed/chunks.jsonl` nằm trên disk.
- File report trong `reports/...` được đăng ký vào bảng `workflow_reports` nếu step
  thành công.
- Report text/json nhỏ được snapshot vào `content_text` hoặc `content_json`.
- Report lớn hơn 2 MB được đánh dấu `content_truncated=true`.

Việc chỉ lưu `reports/...` vào DB giúp DB không bị phình vì các file intermediate như
embeddings, chunks hoặc raw outputs. UI Reports vẫn có thể fallback về filesystem nếu
DB rỗng hoặc chưa có report record.

## Graph Hiện Tại

```text
M00 Runtime
  -> M01 Ingestion
      -> M02 Labeling
          -> M03 RAG
              -> M04 Retrieval
                  -> M06 Extraction
                      -> M07 Verification
M04 Retrieval + M07 Verification
  -> M08 Evaluation
```

| Node | Phụ thuộc | Vai trò |
| --- | --- | --- |
| `m00_runtime` | none | Healthcheck DB, apply migrations, verify pgvector |
| `m01_ingestion` | `m00_runtime` | Discover/download HTML, parse/clean articles, sync articles |
| `m02_labeling` | `m01_ingestion` | Tạo teacher prompts, gọi teacher, validate labels, sync gold labels |
| `m03_rag` | `m01_ingestion`, `m02_labeling` | Chunk articles, embed chunks, build BM25/vector artifacts, gắn pattern refs vào chunks |
| `m04_retrieval` | `m02_labeling`, `m03_rag` | Chạy online retrieval cho articles, ghi contexts/metrics, sync retrieval runs |
| `m06_extraction` | `m04_retrieval` | Chạy student extraction từ M04 contexts |
| `m07_verification` | `m06_extraction` | Modifier giữ verification bật trong M06 |
| `m08_evaluation` | `m04_retrieval`, `m07_verification` | Tạo evaluation reports, metrics và charts |

Không còn node M05 pattern active. Pattern records được tạo trong M03 và đi tiếp qua
metadata của chunk.

## Command Mapping

| Node | Step id | Module command |
| --- | --- | --- |
| `m00_runtime` | `m00_database_healthcheck`, `m00_apply_migrations`, `m00_verify_pgvector` | `python -m finevent.database.cli ...` |
| `m01_ingestion` | `m01_data_ingestion` | `python -m finevent.ingestion ...` |
| `m02_labeling` | `m02_generate_teacher_prompts`, `m02_teacher_labeling`, `m02_validate_labels`, `m02_sync_labels` | `python -m finevent.labeling ...` |
| `m03_rag` | `m03_rag_preparation`, `m03_sync_retrieval` | `python -m finevent.rag ...` |
| `m04_retrieval` | `m04_online_retrieval`, `m04_sync_retrieval_runs` | `python -m finevent.retrieval run-batch ...` |
| `m06_extraction` | `m06_student_batch_extraction` hoặc `m06_m07_extraction_verification` | `python -m finevent.extraction run-batch ...` |
| `m08_evaluation` | `m08_evaluation` | `python -m finevent.evaluation run ...` |

M07 không tạo subprocess riêng. Nếu M07 được chọn, M06 giữ verification bật. Nếu M07
không được chọn, command M06 có thêm `--disable-verification`.

## Config Chính

| Node | Config chính |
| --- | --- |
| `m01_ingestion` | `articles_path`, `input_html_dir`, `html_manifest_path`, `sources`, `max_articles`, `max_discovered_urls`, `min_text_chars`, `discover_download`, `reset_html_snapshots`, `sync_postgres` |
| `m02_labeling` | `max_articles`, `teacher_max_retries`, `generate_prompts`, `run_teacher`, `validate_labels`, `strict_validation`, `sync_postgres` |
| `m03_rag` | `embedding_provider`, `embedding_model`, `embedding_dimension`, `target_words`, `max_words`, `overlap_words`, `patterns_path`, `chunk_patterns_path`, `sync_postgres` |
| `m04_retrieval` | `embedding_provider`, `embedding_model`, `embedding_dimension`, `retrieval_config`, `max_contexts`, `llm_rerank_mode`, `llm_rerank_top_n`, `retrieval_results_path`, `retrieval_metrics_path`, `sync_postgres` |
| `m06_extraction` | `sources`, `limit`, `offset`, `output_path`, `student_provider`, `use_retrieval`, `retrieval_config`, `retrieval_results_path`, `max_contexts`, `sync_postgres` |
| `m08_evaluation` | `gold_path`, `evaluation_output_dir`, `skip_academic_figures` |

Field có `configurable=false` vẫn được trả trong catalog để UI biết contract và
artifact target, nhưng không hiển thị trong form cấu hình nhanh.

## M01 Controls

M01 mặc định `discover_download=true`. Normal run sẽ discover URL từ các source được
chọn, download HTML snapshot, rồi parse thư mục HTML local.

- `sources`: danh sách source dùng riêng cho discovery/download, build thành nhiều
  flag CLI như `--source cafef --source vietstock`.
- `max_articles`: số bài tải tối đa khi discovery/download bật.
- `max_discovered_urls`: số candidate URL tối đa trước khi download.
- `min_text_chars`: số ký tự text tối thiểu sau normalize, không phải số từ.
- `reset_html_snapshots`: chỉ xóa `*.html` trong `input_html_dir` và file
  `html_manifest_path` trước khi chạy M01.

`reset_html_snapshots` không xóa PostgreSQL rows, `articles_clean.jsonl`, reports,
chunks, embeddings, labels, predictions hay downstream artifacts. Nếu bật reset nhưng
tắt discovery/download, M01 sẽ parse thư mục HTML đã rỗng nên raw/clean output có thể
rỗng.

`download_log.jsonl` là log theo từng run. `html_manifest.jsonl` là mapping bền vững
từ HTML snapshot local sang URL gốc. Khi parser tìm thấy entry trong manifest,
`article.url` sẽ là URL gốc và `article.raw_html_path` lưu local file. Nếu không có
manifest entry, parser fallback về `file://...` như trước và vẫn lưu `raw_html_path`.

### Ví Dụ Command M01

Config:

```json
{
  "sources": ["cafef", "vietstock"],
  "discover_download": true,
  "max_articles": 25,
  "max_discovered_urls": 80,
  "reset_html_snapshots": true
}
```

Command được build theo dạng:

```text
python -m finevent.ingestion
  --input-html-dir data/raw/html
  --html-manifest-path data/raw/html_manifest.jsonl
  --raw-output-path data/raw/articles_raw.jsonl
  --clean-output-path data/processed/articles_clean.jsonl
  --report-path reports/data/data_quality_summary.md
  --min-text-chars 300
  --reset-html-snapshots
  --discover
  --max-discovered-urls 80
  --max-download-articles 25
  --source cafef
  --source vietstock
  --sync-postgres
```

Nếu `sources=[]` và `discover_download=true`, backend trả
`INVALID_WORKFLOW_CONFIG`. Đây là lỗi config, không phải lỗi runtime.

## M02 Controls

Normal mode của M02 là full flow:

1. `generate_prompts=true`: tạo `teacher_prompts.jsonl` từ clean articles.
2. `run_teacher=true`: gọi teacher LLM cho các prompt đó.
3. `validate_labels=true`: validate teacher output thành gold/rejected labels.
4. `sync_postgres=true`: sync labels/events vào PostgreSQL.

`max_articles` là số prompt/article record tối đa được chọn cho run. Retry của LLM
không tính là article mới. Ví dụ `max_articles=25` nghĩa là chọn tối đa 25 prompt
records; `teacher_max_retries` chỉ là số lần thử lại cho mỗi prompt đã chọn.

`strict_validation` mặc định `true`. Khi bật strict validation, chỉ label `PASS` mới
vào `events_gold.jsonl`; output lỗi schema/taxonomy/grounding vào
`events_rejected.jsonl`.

`label_reason` và `event_reason` là field bắt buộc. Teacher prompt yêu cầu teacher
model sinh reason ngắn, grounded theo bài, thay vì dùng boilerplate sinh sau.

### Ý Nghĩa Các Switch M02

Các checkbox M02 chủ yếu phục vụ resume/debug:

| Config | Khi bật | Khi tắt |
| --- | --- | --- |
| `generate_prompts` | Tạo lại `teacher_prompts.jsonl` từ clean articles | Dùng lại prompt file cũ |
| `run_teacher` | Gọi teacher LLM và ghi `teacher_outputs.jsonl` | Dùng lại teacher output cũ |
| `validate_labels` | Validate output thành gold/rejected labels | Không tạo lại gold/rejected labels |
| `strict_validation` | Chỉ `PASS` vào gold | Có thể cho label warning vào gold tùy validator |

Normal run nên bật đủ `generate_prompts`, `run_teacher`, `validate_labels` và
`strict_validation`. Chỉ tắt khi cố ý resume từ artifact cũ hoặc debug một bước cụ
thể.

## Contract M03, M04, M06

M03 là bước chuẩn bị offline. M03 chunk articles, embed chunks, build BM25/vector
artifacts, build gold-derived pattern records, rồi gắn `pattern_refs` vào matching
chunks. Không có vector index riêng cho patterns.

M04 là bước online retrieval preparation. M04 chạy retrieval strategy theo từng
article và ghi context record sẵn sàng cho M06 vào
`data/retrieval/online_contexts.jsonl`. Retrieval metrics được sinh ở M04 khi có gold
labels. Strategy hiện có:

- `bm25_only`
- `dense_only`
- `hybrid`
- `metadata_aware_hybrid`
- `rule_aware_rerank`
- `llm_reasoning_rerank`
- `multi_event_aware_hybrid`

Trong catalog UI, `retrieval_config` là recipe tính điểm/rerank cho context pack, không
phải lựa chọn một nguồn retrieve duy nhất. Các recipe hybrid vẫn combine BM25, dense
embedding, metadata, rule/LLM rerank và selection strategy. Luồng compare nhiều recipe
vẫn tồn tại ở `python -m finevent.retrieval compare`; graph M04 `run-batch` chọn một
recipe vì M06 cần một artifact context xác định để chạy extraction.

M04 graph run mặc định thêm listwise LLM rerank bằng `llm_rerank_mode=student_env`.
Backend truyền các flag `--llm-rerank-mode student_env` và `--llm-rerank-top-n 15` cho
`finevent.retrieval run-batch`. Mode này dùng student model cấu hình trong `.env` để
xếp hạng lại pool đã qua scoring/strategy selection trước khi ghi
`online_contexts.jsonl`. Với `multi_event_aware_hybrid`, coverage/MMR vẫn chạy trước
LLM rerank; backend chỉ giữ pool trước LLM rộng hơn context cuối để LLM có đủ ứng viên
lọc lại. Khi chạy local không muốn gọi API, admin có thể đổi sang `deterministic`
hoặc `off`.

M06 không tự retrieve chunk nữa. M06 load record M04 khớp `article_id` và
`retrieval_config`, cắt số context bằng `max_contexts`, rồi đưa từng context cùng
`pattern_refs` gắn trên chunk vào extraction prompt.

## M04 Và M06 Không Chạy Hai Retrieval Luồng

Thiết kế cũ có ý tưởng retrieve chunks và retrieve patterns riêng. Thiết kế hiện tại
không làm vậy nữa.

Luồng đúng:

```text
M03: chunk -> attach pattern_refs
M04: retrieve chunks -> carry pattern_refs in contexts
M06: prompt contexts + matched_patterns from those contexts
```

Lý do:

- Pattern chỉ có ý nghĩa khi gắn với evidence chunk cụ thể.
- Nếu retrieve pattern riêng, prompt có thể nhận pattern không liên quan trực tiếp
  đến context đang được dùng.
- M04 là nơi duy nhất đánh giá retrieval quality; M06 chỉ đánh giá extraction quality.
- Debug dễ hơn vì mỗi event extraction có thể truy ngược về context chunk và pattern
  refs đi cùng chunk đó.

## Các Điểm Cắt Text/Content

Các điểm cắt có chủ ý hiện tại:

| Khu vực | Giới hạn | Mục đích |
| --- | --- | --- |
| M03 chunking | `max_words` mỗi chunk | Giữ chunk ổn định, tôn trọng paragraph/section |
| M06 article text trong prompt | `max_article_chars`, mặc định `2200` | Giữ prompt extraction có kích thước kiểm soát được |
| M06 context text | `max_context_chars`, mặc định `450` mỗi context | Tránh context chiếm toàn bộ prompt |
| M06 matched pattern output | `max_pattern_output_chars`, mặc định `700` mỗi pattern output view | Giữ ví dụ pattern compact |
| M06 total prompt | `max_prompt_chars`, mặc định `11000` | Nếu quá dài thì fallback sang ít context hơn |
| Verification prompt | article `4000`, context `1200` ký tự | Giới hạn prompt verifier |
| Report DB snapshot | `2_000_000` bytes mỗi text report | Lưu preview report mà không nhét file quá lớn vào DB |

Fallback của M06: full contexts, top 3 contexts ngắn hơn, top 1 context ngắn hơn,
rồi không có retrieval context nếu vẫn vượt `max_prompt_chars`.

## Lưu Report Vào DB

Khi workflow step thành công, job runner đăng ký expected artifacts nằm dưới
`reports/...` vào PostgreSQL table `workflow_reports`.

Các field lưu gồm `run_id`, `workflow_name`, `step_id`, path/name/kind, file size,
`content_text` hoặc `content_json`, `content_truncated` và metadata. Artifact không
nằm trong `reports/...` vẫn nằm trên disk, không copy vào bảng này.

Admin report API đọc từ `workflow_reports` khi PostgreSQL khả dụng và fallback về
filesystem discovery khi DB không sẵn sàng.

## Validation Rules

| Trường hợp | Error code |
| --- | --- |
| `workflow_name` không tồn tại | `UNKNOWN_WORKFLOW` |
| Thiếu `config.selected_nodes` cho graph workflow | `INVALID_WORKFLOW_CONFIG` |
| Danh sách selected node rỗng | `INVALID_WORKFLOW_CONFIG` |
| Thiếu dependency | `INVALID_WORKFLOW_CONFIG` |
| M01 `discover_download=true` nhưng `sources=[]` | `INVALID_WORKFLOW_CONFIG` |
| Node được chọn nhưng không sinh runnable step | `INVALID_WORKFLOW_CONFIG` |
| Queue đầy | `RUN_QUEUE_FULL` |

Backend sort selected nodes theo registry order, không theo thứ tự caller gửi lên.

## Source Filtering Cho M06

M06 có thể lọc clean articles theo `sources`. Khi dùng filter, registry ghi:

```text
runs/admin/{run_id}/inputs/articles_filtered.jsonl
```

File gốc `articles_clean.jsonl` không bị sửa.

## Cách Thêm Node

1. Thêm `src/finevent/api/workflow_registry/nodes/mXX_*.py`.
2. Khai báo `node_spec = WorkflowNodeSpec(...)`.
3. Implement `build_steps(context)` và chỉ build command từ allowlist code-side.
4. Import node spec trong `workflow_registry/nodes/__init__.py`.
5. Thêm edge label vào `EDGE_LABELS` nếu UI cần.
6. Cập nhật frontend `WorkflowNodeId`, node order, presentation metadata và graph position.
7. Cập nhật test và tài liệu này.

Check:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_admin_api.py
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m ruff check src/finevent/api tests/test_admin_api.py
```
