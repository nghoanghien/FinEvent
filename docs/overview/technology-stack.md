# Long-term Technology Stack and Storage Architecture

## Mục tiêu

Tài liệu này chốt bộ công nghệ nên dùng lâu dài cho FinEvent-VN. Mục tiêu là xây project chỉnh chu ngay từ đầu, có thể nâng cấp dữ liệu, workflow, retrieval, evaluation và demo app mà không phải thay đổi kiến trúc quá nhiều về sau.

Nguyên tắc chọn stack:

- Có đường nâng cấp rõ từ đồ án nhỏ lên hệ thống lớn hơn.
- Tránh phụ thuộc vào công nghệ chỉ hợp prototype.
- Core logic tách khỏi app demo.
- Dữ liệu có source of truth rõ ràng.
- Workflow, model call, prompt, retrieval config và evaluation đều version được.
- Có thể chạy local bằng Docker Compose, nhưng vẫn gần với production.

## Quyết định tổng thể

| Nhóm | Công nghệ mặc định v1 | Dùng để làm gì | Lý do chọn |
| --- | --- | --- | --- |
| Ngôn ngữ | Python 3.11+ | Viết crawler, preprocessing, retrieval, evaluation, workflow, API backend và demo app | Hệ sinh thái NLP/ML mạnh, ổn định, dễ triển khai |
| Python environment | Miniconda + `environment.yml` | Quản lý Python env, dependency ML/NLP, package native, CUDA/GPU nếu cần | Bạn đã cài Miniconda; conda phù hợp project ML lâu dài và dễ tái lập môi trường |
| Python package manager | `uv` + `pyproject.toml` + `requirements.lock` | Khai báo, lock và cài pip dependencies bên trong conda env đã activate | Conda giữ môi trường/native deps; `uv` giúp cài nhanh và lock dependency Python |
| Project metadata | `pyproject.toml` | Lưu package metadata, dependency groups, Ruff/Pyright/pytest config | Giữ project chuẩn Python và dùng được với `uv` |
| Code quality | Ruff + Pyright hoặc mypy + pytest | Format/lint/type check/test | Giữ code sạch khi project lớn dần |
| Config | `.env` + YAML + Pydantic Settings | Quản lý API key, DB URL, model name, prompt version, retrieval config | Có validation config, dễ đổi giữa local/dev/prod |
| Raw storage | JSONL + HTML files | Lưu bài báo raw, clean article, labels, logs và raw HTML để debug parser | Dễ đọc, dễ version, phù hợp pipeline batch |
| Primary DB | PostgreSQL | Lưu articles, metadata, chunks, labels, patterns, runs, metrics | Source of truth lâu dài, dễ migration, query tốt |
| DB migration/ORM | SQLAlchemy + Alembic | Quản lý schema DB và migration | Tránh sửa DB thủ công khi schema thay đổi |
| Vector search mặc định | PostgreSQL + pgvector | Lưu embedding và query vector ngay trong DB chính | Giảm split storage, metadata + vector cùng một nơi |
| Vector experiment baseline | FAISS | Chạy dense retrieval baseline offline và so sánh Recall@K/tốc độ | Nhẹ, nhanh, phù hợp ablation, không làm source of truth |
| Lexical retrieval | PostgreSQL full-text/trigram + Python BM25 experiments | Tìm bài/chunk theo keyword tài chính như `trúng thầu`, `tăng vốn`, `bổ nhiệm` | Bù cho embedding khi keyword sự kiện rõ; đủ dùng trước khi cần OpenSearch |
| Workflow runtime | LangGraph | Điều phối online workflow: preprocess -> retrieve -> rerank -> extract -> verify | Có state rõ, dễ trace từng node và hiển thị trên app demo |
| Batch jobs | Typer CLI trước, Prefect optional khi cần schedule | Chạy crawl, labeling, indexing, evaluation theo batch | Bắt đầu đơn giản, có đường nâng cấp sang orchestration |
| API backend | FastAPI | Cung cấp API cho extraction workflow, retrieval, evaluation, frontend UI | Chuẩn OpenAPI, tách backend khỏi frontend |
| LLM integration | LangChain model interfaces | Chuẩn hóa cách gọi teacher LLM, student LLM, rerank LLM, repair LLM | Dùng trực tiếp LangChain, giảm code hạ tầng và dễ đổi provider |
| Validation | Pydantic hoặc JSON Schema | Kiểm tra output JSON, enum, required fields, evidence fields | Bắt output đúng schema trước khi lưu/evaluate |
| Experiment tracking | MLflow hoặc artifact logs chuẩn hóa | Lưu run config, metrics, model/prompt/retrieval version | Giúp so sánh thí nghiệm lâu dài |
| Evaluation | pandas, numpy, scikit-learn, optional `ir-measures`/`ranx` | Tính retrieval metrics, extraction metrics, hallucination metrics, export report | Đủ cho metric định lượng và bảng báo cáo |
| Frontend | Next.js + TypeScript | UI nhập URL/text, hiển thị retrieval trace, patterns, event table, verification report | Phù hợp làm lâu dài hơn demo-only UI, dễ mở rộng thành product |
| Container | Docker Compose | Chạy Postgres/pgvector, API backend và Next.js frontend | Môi trường giống nhau giữa các máy |

## Stack mặc định lâu dài

Nếu làm chỉnh chu từ đầu, nên dùng bộ mặc định sau:

```text
Python 3.11+
Miniconda + environment.yml
uv + pyproject.toml + requirements.lock inside the conda env
FastAPI backend
Next.js frontend
LangGraph workflow runtime
PostgreSQL + pgvector as source of truth and default vector search
SQLAlchemy + Alembic for DB schema
Pydantic for validation
LangChain for LLM model calls
Typer CLI for batch scripts
pandas/numpy/scikit-learn for evaluation
Docker Compose for local infrastructure
```

Cách phối hợp `Miniconda` và `uv`:

- `environment.yml` giữ Python version, conda channels, native dependencies và `uv`.
- `pyproject.toml` giữ Python package dependencies, optional dependency groups và tool config.
- `requirements.lock` được sinh từ `pyproject.toml` bằng `uv pip compile`.
- Sau khi `conda activate finevent-vn`, dùng `uv pip sync requirements.lock` để cài package vào chính conda env đang active.
- Không dùng `uv sync` làm mặc định trong v1 nếu muốn tránh việc `uv` tự tạo `.venv` riêng ngoài conda env.

ChromaDB và SQLite chỉ nên dùng khi cần prototype rất nhanh. Nếu đã xác định làm lâu dài, không nên lấy SQLite/ChromaDB làm mặc định vì sau này dễ phải migration sang PostgreSQL/vector service.

## Đường nâng cấp không phá kiến trúc

| Khi nào | Nâng cấp | Vì sao không phá kiến trúc |
| --- | --- | --- |
| Corpus nhỏ, đồ án local | PostgreSQL + pgvector | Vừa structured DB vừa vector search |
| Corpus lớn hơn, vector search chậm | Tối ưu pgvector bằng HNSW/IVFFlat, partitioning, materialized embedding tables | Vẫn giữ PostgreSQL + pgvector, không đổi DB/vector backend |
| Keyword search tiếng Việt cần mạnh hơn | Thêm OpenSearch/Elasticsearch | Retrieval interface giữ nguyên, chỉ đổi backend lexical |
| Batch jobs nhiều, cần schedule | Thêm Prefect | Các scripts đã tách thành task/CLI nên dễ wrap |
| Demo cần thành sản phẩm | Giữ FastAPI + Next.js | API contract và UI framework đều dùng được lâu dài |
| Model provider thay đổi | Đổi LangChain integration/config | Workflow node không đổi |

## Công nghệ theo module

### Crawling and preprocessing

| Công nghệ | Dùng để làm gì | Output liên quan |
| --- | --- | --- |
| `requests` | Tải HTML từ các trang báo tĩnh | `articles_raw.jsonl`, raw HTML |
| Playwright | Tải trang cần render JavaScript hoặc chống lazy-load | raw HTML cho source khó crawl |
| `BeautifulSoup` | Parse HTML theo rule từng source | title, date, body text |
| `trafilatura` | Trích nội dung chính của bài báo, giảm menu/quảng cáo | clean text baseline |
| Python regex + Unicode normalization | Chuẩn hóa whitespace, ngày tháng, ký hiệu tài chính, text tiếng Việt | `articles_clean.jsonl` |
| `hashlib` | Tạo `content_hash` để deduplicate và cache embedding | dedup report, embedding cache |
| `pandas` | Kiểm tra chất lượng dữ liệu và thống kê source/ticker/keyword | `data_quality_summary.md` |

### Storage and artifact management

| Công nghệ | Dùng để làm gì | Ghi chú |
| --- | --- | --- |
| Miniconda | Tạo và quản lý Python environment | Dùng `environment.yml` làm nguồn tái lập env |
| `environment.yml` | Khai báo Python version, conda deps, native deps và `uv` | Phù hợp ML/NLP vì nhiều package native |
| `uv` | Compile/sync Python pip dependencies nhanh trong conda env | Dùng nhóm lệnh `uv pip ...`, không để `uv` tạo env riêng trong v1 |
| `pyproject.toml` | Khai báo package metadata, dependency groups và tool config | Source cho `uv pip compile` |
| `requirements.lock` | Lock Python pip dependencies đã resolve | Dùng với `uv pip sync` để tái lập package set |
| JSONL | Lưu raw articles, clean articles, labels, predictions, logs | Dễ append, dễ đọc bằng pandas |
| Raw HTML files | Giữ bản HTML gốc để debug parser | Không dùng cho model trực tiếp |
| PostgreSQL | Lưu articles, metadata, chunks, labels, patterns, runs, metrics | Source of truth lâu dài |
| pgvector | Lưu embedding và query vector trong PostgreSQL | Vector backend mặc định |
| FAISS | Lưu vector index baseline offline | Cần file metadata mapping riêng |
| YAML config | Lưu cấu hình experiment, retrieval, workflow | Mỗi run phải log config version |
| `.env` | Lưu secret/API key ngoài git | Không commit key thật |

### Embedding, retrieval and reranking

| Công nghệ | Dùng để làm gì | Vai trò trong workflow |
| --- | --- | --- |
| Cloudflare embedding | Embedding baseline đã setup sẵn | Sinh vector cho article/chunk/pattern |
| BGE-M3 | Embedding multilingual để so sánh retrieval | Experiment embedding comparison |
| Multilingual E5 | Semantic retrieval baseline phổ biến | Experiment embedding comparison |
| GTE multilingual | Embedding so sánh thêm nếu đủ thời gian | Experiment embedding comparison |
| PostgreSQL full-text/trigram | Lexical retrieval theo keyword/tên công ty | Stage 1 lexical retrieval |
| BM25 Python baseline | Baseline lexical retrieval trong thí nghiệm | So sánh với vector/hybrid |
| pgvector similarity search | Dense vector retrieval mặc định | Stage 1/2 retrieval |
| Metadata-aware scoring | Boost theo ticker, company, source, time | Giảm context sai công ty/sai sự kiện |
| Rule-aware rerank | Rerank theo event keyword, ticker/company, NO_EVENT signals | Lọc nhanh trước khi gọi LLM |
| LLM reasoning rerank | LLM đọc candidate và chấm relevance theo logic sự kiện | Lọc top context cuối cùng cho extraction |

### LLM, workflow and prompting

| Công nghệ | Dùng để làm gì | Ghi chú |
| --- | --- | --- |
| Teacher LLM | Sinh AI-generated gold labels và pattern examples | Output được auto validate, không human review |
| Student LLM 7B/8B | Sinh event JSON trong workflow vận hành/demo | Không fine-tune toàn bộ trong v1 |
| Repair LLM prompt | Sửa JSON lỗi format/schema mà không thêm fact mới | Chỉ repair, không đổi nội dung không có evidence |
| Self-verification prompt | Kiểm tra field có được article/context hỗ trợ không | Dùng trong hallucination reduction |
| LangGraph | Điều phối online workflow nhiều node | Trace rõ từng bước |
| LangChain | Gọi LLM provider/model, prompt templates, output parser nếu cần | Không tự triển khai lớp gọi model riêng |
| Prompt templates versioned | Quản lý prompt extraction/rerank/repair/verify | Mỗi run log `prompt_version` |
| FastAPI | Expose workflow qua API | Next.js frontend gọi API này |
| Next.js + TypeScript | Xây frontend nhập bài báo, xem workflow trace, xem bảng event | UI lâu dài, tách khỏi backend |

### Validation, evaluation and reporting

| Công nghệ | Dùng để làm gì | Metric/report |
| --- | --- | --- |
| Pydantic | Định nghĩa schema output bằng Python model | JSON validity, schema compliance |
| JSON Schema | Validate output độc lập với Python code nếu cần | Có thể dùng cho app/API |
| `scikit-learn` | Tính precision, recall, F1, macro/micro metrics | extraction metrics |
| `numpy` | Tính ranking metrics và xử lý score arrays | MRR, nDCG |
| `pandas` | Tổng hợp predictions, errors, metrics by run | CSV report |
| matplotlib/seaborn | Vẽ biểu đồ distribution/metric nếu cần | figures cho báo cáo |
| Next.js | Trình diễn workflow và output | frontend app |
| MLflow hoặc structured artifact logs | Lưu run config, metrics, artifacts | experiment tracking |

## Cấu trúc dữ liệu trên filesystem

```text
data/
  raw/
    articles_raw.jsonl
    html/
  processed/
    articles_clean.jsonl
    chunks.jsonl
  labels/
    events_ai_generated.jsonl
    events_gold.jsonl
    events_rejected.jsonl
  patterns/
    patterns.jsonl
  vector_store/
    faiss/
  retrieval/
    retrieval_logs.jsonl
runs/
  extraction/
  evaluation/
reports/
  evaluation/
```

Infrastructure local nên chạy bằng Docker Compose:

```text
infra/
  docker-compose.yml
  postgres/
    init.sql
```

PostgreSQL volume sẽ lưu database chính. Embedding và metadata đều được lưu/query qua pgvector để tránh phải đồng bộ thêm một vector database riêng.

## PostgreSQL schema v1

PostgreSQL lưu dữ liệu có cấu trúc, trace thí nghiệm và embedding qua pgvector. Các cột JSON nên dùng `JSONB`; thời gian nên dùng `TIMESTAMPTZ`; embedding nên dùng kiểu `vector(n)` nếu dimension cố định.

### `articles`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `article_id` | TEXT PRIMARY KEY | ID ổn định |
| `source` | TEXT | cafef, vietstock, fireant |
| `url` | TEXT | URL gốc |
| `title` | TEXT | Tiêu đề |
| `published_at` | TEXT | ISO 8601 |
| `clean_text_path` | TEXT | Đường dẫn text/jsonl |
| `content_hash` | TEXT | Dedup |
| `language` | TEXT | `vi` |
| `created_at` | TEXT | Thời điểm ingest |

### `article_metadata`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `article_id` | TEXT | Khóa ngoại |
| `tickers_hint` | JSONB | JSON array |
| `company_names_hint` | JSONB | JSON array |
| `sector_hint` | TEXT | Ngành nếu có |
| `event_keywords` | JSONB | JSON array |
| `metadata_confidence` | REAL | Độ tin cậy metadata |

### `chunks`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `chunk_id` | TEXT PRIMARY KEY | ID chunk |
| `article_id` | TEXT | Thuộc bài nào |
| `chunk_index` | INTEGER | Thứ tự chunk |
| `chunk_level` | TEXT | `document`, `section`, `paragraph` |
| `text` | TEXT | Nội dung chunk |
| `token_count` | INTEGER | Ước lượng token |
| `content_hash` | TEXT | Cache embedding |
| `metadata_json` | JSONB | Metadata dạng JSON |
| `embedding` | vector(n) | Optional nếu lưu chunk embedding trực tiếp bằng pgvector |

### `events_gold`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `event_id` | TEXT PRIMARY KEY | ID event |
| `article_id` | TEXT | Bài nguồn |
| `document_label` | TEXT | `HAS_EVENT` hoặc `NO_EVENT` |
| `event_type` | TEXT | Taxonomy chính |
| `event_subtype` | TEXT | Subtype nếu có |
| `impact_sentiment` | TEXT | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED` |
| `event_json` | JSONB | JSON đầy đủ theo schema |
| `teacher_model` | TEXT | Model sinh nhãn |
| `validation_status` | TEXT | `PASS`, `REPAIRED`, `REJECTED` |

### `extraction_runs`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `run_id` | TEXT PRIMARY KEY | ID lần chạy |
| `article_id` | TEXT | Bài đầu vào |
| `workflow_config` | JSONB | Config LangGraph |
| `model_name` | TEXT | Student LLM |
| `prompt_version` | TEXT | Prompt dùng |
| `retrieval_config` | TEXT | Retrieval config |
| `output_json` | JSONB | Output đã validate |
| `validation_errors` | JSONB | JSON array |
| `latency_ms` | INTEGER | Latency |

## Vector store

### pgvector mặc định

pgvector là lựa chọn mặc định lâu dài vì metadata, structured fields và vectors đều nằm trong PostgreSQL. Điều này giảm rủi ro lệch dữ liệu giữa relational DB và vector DB.

Các bảng gợi ý:

- `article_embeddings`
- `chunk_embeddings`
- `pattern_embeddings`

Mỗi record embedding cần có:

```json
{
  "embedding_id": "emb_chunk_001",
  "object_type": "chunk",
  "object_id": "cafef_hpg_20260115_001_c03",
  "embedding_model": "bge-m3",
  "embedding_dimension": 1024,
  "content_hash": "sha256:...",
  "created_at": "..."
}
```

Index gợi ý:

- HNSW cho query online cần latency tốt.
- IVFFlat nếu cần thử speed/recall trade-off khác.
- B-tree/GIN indexes cho metadata filter như ticker, source, event type.

### FAISS baseline

FAISS dùng để so sánh tốc độ và Recall@K. Vì FAISS không quản lý metadata thuận tiện như ChromaDB, cần lưu mapping riêng:

```text
data/vector_store/faiss/index.faiss
data/vector_store/faiss/metadata.jsonl
```

### ChromaDB prototype-only

ChromaDB có thể dùng nếu cần prototype cực nhanh, nhưng không nên là mặc định lâu dài nếu đã muốn làm project chỉnh chu. Lý do: project vẫn cần PostgreSQL cho metadata, labels, runs và evaluation; dùng ChromaDB song song ngay từ đầu tạo thêm một nguồn dữ liệu cần đồng bộ.

## Embedding models

Thí nghiệm nên so sánh tối thiểu 3 nhóm:

| Nhóm | Vai trò |
| --- | --- |
| Cloudflare embedding | Baseline vì đã setup sẵn |
| BGE-M3 | Multilingual mạnh, phù hợp retrieval |
| Multilingual E5 | Baseline phổ biến cho semantic retrieval |
| GTE multilingual | So sánh thêm nếu đủ thời gian |
| Vietnamese embedding model | Optional, dùng nếu chọn được model ổn định |

Mỗi vector phải log:

- `embedding_model`
- `embedding_dimension`
- `embedding_version`
- `created_at`
- `content_hash`

## Workflow runtime

### Batch workflow

Dùng script Python thường cho:

- crawl
- clean
- chunk
- embed
- build index
- teacher labeling
- evaluation

Lý do: dễ chạy lại theo batch và dễ log artifact.

### Online workflow

Dùng LangGraph cho luồng nhập bài báo và trích xuất:

```text
input_article
  -> preprocess
  -> query_rewrite
  -> retrieve
  -> rerank
  -> select_patterns
  -> extract_events
  -> verify_grounding
  -> repair_if_needed
  -> final_output
```

LangGraph được chọn vì mỗi node có input/output rõ, dễ debug và dễ hiển thị trên app demo.

## API backend and frontend

### FastAPI backend

FastAPI là backend chính cho long-term stack.

Dùng để expose:

- `POST /extract`: chạy workflow từ URL/text đến event table.
- `GET /runs/{run_id}`: xem trace một lần chạy.
- `GET /articles/{article_id}`: xem article metadata.
- `GET /events`: query event table.
- `POST /evaluate`: chạy evaluation config nếu cần.

Lý do tách FastAPI khỏi frontend:

- khó test API contract.
- khó deploy nhiều client.
- logic dễ bị trộn vào UI nếu frontend gọi trực tiếp core modules.

### Next.js frontend

Next.js là frontend chính:

- nhập URL/text.
- gọi FastAPI.
- hiển thị retrieval trace, patterns, event table, verification report.
- export JSON/CSV.

Frontend chỉ quản lý UI state và gọi API. Core workflow, retrieval, extraction và verification vẫn nằm ở Python backend.

Frontend stack đề xuất:

- Next.js App Router.
- TypeScript.
- Tailwind CSS hoặc shadcn/ui nếu muốn UI nhanh và nhất quán.
- TanStack Query nếu cần quản lý API state/cache.
- Zod optional để validate response type phía frontend.

## Model serving

Student LLM 7B/8B có thể chạy qua một trong các cách:

- API nội bộ nếu đã có endpoint.
- vLLM nếu có GPU.
- Ollama/llama.cpp nếu chạy local nhẹ.
- Cloud API nếu demo cần ổn định.

Teacher LLM dùng để sinh gold labels và patterns. Output teacher được chấp nhận sau auto validation, không có human review.

## Config đề xuất

```yaml
storage:
  postgres_dsn: postgresql+psycopg://finevent:password@localhost:5432/finevent
  vector_backend: pgvector
  artifact_dir: data

embedding:
  default_model: cloudflare_default
  cache_by_content_hash: true

retrieval:
  top_k_stage1: 50
  top_k_stage2: 20
  top_k_final: 5
  hybrid_alpha: 0.55
  hybrid_beta: 0.25
  metadata_gamma: 0.20

workflow:
  engine: langgraph
  enable_llm_reasoning_rerank: true
  enable_self_verification: true

api:
  backend: fastapi
  host: 0.0.0.0
  port: 8000

extraction:
  student_model: qwen_or_llama_8b
  prompt_version: v1
  max_repair_attempts: 2
```

## Nâng cấp sau v1

| Nâng cấp | Khi nào cần |
| --- | --- |
| pgvector index tuning | Corpus lớn hơn, query vector chậm hoặc cần cân bằng recall/latency bằng HNSW/IVFFlat |
| Elasticsearch/OpenSearch | Cần lexical/BM25 mạnh, filter phức tạp, nhiều query text |
| Prefect | Batch crawl/index/evaluation cần schedule và retry UI |
| MinIO/S3-compatible storage | Artifact lớn, nhiều HTML/log/model output |
| Fine-tuned embedding | Retrieval Recall@K thấp dù đã hybrid/rerank |
| Fine-tuned reranker | LLM reasoning rerank quá đắt hoặc chậm |
| Component library | UI nhiều màn hình, cần form/table/dialog nhất quán |

## Nguồn tham khảo chính

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview): LangGraph được chọn cho workflow stateful vì official docs mô tả nó là orchestration runtime cho long-running, stateful workflows, có persistence, streaming, human-in-the-loop và fault tolerance.
- [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview): LangChain được dùng trực tiếp cho model calls vì official docs nhấn mạnh standard model interface giúp đổi provider và giảm lock-in.
- [Miniconda documentation](https://www.anaconda.com/docs/getting-started/miniconda/main): Miniconda được dùng làm môi trường Python vì là bản cài tối giản gồm conda, Python và các package nền, phù hợp quản lý dependency ML/NLP lâu dài.
- [uv environment docs](https://docs.astral.sh/uv/pip/environments/): `uv pip` có thể làm việc với môi trường conda đang active, nên project dùng `uv` bên trong Miniconda thay vì thay thế Miniconda.
- [pgvector official repository](https://github.com/pgvector/pgvector): pgvector được chọn làm vector backend mặc định vì hỗ trợ vector similarity search trong PostgreSQL, gồm exact/approximate nearest neighbor search và nhiều distance metrics.
- [FastAPI features](https://fastapi.tiangolo.com/features/): FastAPI được chọn cho backend vì hỗ trợ Python type hints, OpenAPI/JSON Schema docs và phù hợp xây API service.
- [Next.js docs](https://nextjs.org/docs): Next.js được chọn cho frontend vì hỗ trợ App Router, Server/Client Components, data fetching, routing và production deployment.
