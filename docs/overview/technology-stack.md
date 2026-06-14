# Technology Stack and Storage Architecture

## Mục tiêu

Tài liệu này chốt công nghệ mặc định để triển khai FinEvent-VN. Mục tiêu là đủ rõ để code ngay, đồng thời vẫn giữ khả năng mở rộng khi cần làm thêm thí nghiệm.

## Quyết định tổng thể

| Nhóm | Công nghệ mặc định v1 | Dùng để làm gì | Lý do chọn |
| --- | --- | --- | --- |
| Ngôn ngữ | Python 3.10+ | Viết crawler, preprocessing, retrieval, evaluation, workflow và app demo | Hệ sinh thái NLP/ML mạnh, dễ kết hợp Streamlit và các thư viện vector DB |
| Config | `.env` + YAML | Quản lý API key, đường dẫn dữ liệu, model name, prompt version, retrieval config | Dễ đổi cấu hình giữa các thí nghiệm mà không sửa code |
| Raw storage | JSONL + HTML files | Lưu bài báo raw, clean article, labels, logs và raw HTML để debug parser | Dễ đọc, dễ version, phù hợp pipeline batch |
| Structured DB | SQLite | Lưu metadata bài báo, chunks, gold labels, extraction runs và run trace | Gọn, chạy local tốt, đủ cho demo và evaluation v1 |
| Vector DB | ChromaDB | Lưu embedding của chunks/documents/patterns và search theo vector + metadata | Có metadata filtering, tiện cho RAG local |
| Vector baseline | FAISS | Chạy dense retrieval baseline và so sánh tốc độ/Recall@K | Nhẹ, nhanh, phù hợp ablation |
| Lexical retrieval | BM25 | Tìm bài/chunk theo keyword tài chính như `trúng thầu`, `tăng vốn`, `bổ nhiệm` | Bù cho embedding khi keyword sự kiện rất rõ |
| Workflow runtime | LangGraph | Điều phối online workflow: preprocess -> retrieve -> rerank -> extract -> verify | Có state rõ, dễ trace từng node và hiển thị trên app demo |
| LLM wrapper | Adapter tự viết, có thể dùng LangChain wrapper nếu tiện | Chuẩn hóa cách gọi teacher LLM, student LLM, rerank LLM, repair LLM | Tránh phụ thuộc quá nặng vào chain framework, dễ thay model |
| Validation | Pydantic hoặc JSON Schema | Kiểm tra output JSON, enum, required fields, evidence fields | Bắt output đúng schema trước khi lưu/evaluate |
| Evaluation | pandas, numpy, scikit-learn | Tính retrieval metrics, extraction metrics, hallucination metrics, export CSV/report | Đủ cho metric định lượng và bảng báo cáo |
| Demo | Streamlit | UI nhập URL/text, hiển thị retrieval trace, patterns, event table, verification report | Dựng demo nhanh, phù hợp đồ án |

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
| JSONL | Lưu raw articles, clean articles, labels, predictions, logs | Dễ append, dễ đọc bằng pandas |
| Raw HTML files | Giữ bản HTML gốc để debug parser | Không dùng cho model trực tiếp |
| SQLite | Lưu structured metadata, chunks, labels, extraction run logs | DB mặc định cho v1 |
| ChromaDB | Lưu vector embeddings và metadata filter | Vector DB mặc định |
| FAISS | Lưu vector index baseline | Cần file metadata mapping riêng |
| YAML config | Lưu cấu hình experiment, retrieval, workflow | Mỗi run phải log config version |
| `.env` | Lưu secret/API key ngoài git | Không commit key thật |

### Embedding, retrieval and reranking

| Công nghệ | Dùng để làm gì | Vai trò trong workflow |
| --- | --- | --- |
| Cloudflare embedding | Embedding baseline đã setup sẵn | Sinh vector cho article/chunk/pattern |
| BGE-M3 | Embedding multilingual để so sánh retrieval | Experiment embedding comparison |
| Multilingual E5 | Semantic retrieval baseline phổ biến | Experiment embedding comparison |
| GTE multilingual | Embedding so sánh thêm nếu đủ thời gian | Experiment embedding comparison |
| BM25 | Lexical retrieval theo keyword | Stage 1 retrieval |
| ChromaDB similarity search | Dense vector retrieval | Stage 1/2 retrieval |
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
| Prompt templates versioned | Quản lý prompt extraction/rerank/repair/verify | Mỗi run log `prompt_version` |

### Validation, evaluation and reporting

| Công nghệ | Dùng để làm gì | Metric/report |
| --- | --- | --- |
| Pydantic | Định nghĩa schema output bằng Python model | JSON validity, schema compliance |
| JSON Schema | Validate output độc lập với Python code nếu cần | Có thể dùng cho app/API |
| `scikit-learn` | Tính precision, recall, F1, macro/micro metrics | extraction metrics |
| `numpy` | Tính ranking metrics và xử lý score arrays | MRR, nDCG |
| `pandas` | Tổng hợp predictions, errors, metrics by run | CSV report |
| matplotlib/seaborn | Vẽ biểu đồ distribution/metric nếu cần | figures cho báo cáo |
| Streamlit | Trình diễn workflow và output | demo app |

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
  db/
    finevent_vn.sqlite
  vector_store/
    chroma/
    faiss/
  retrieval/
    retrieval_logs.jsonl
runs/
  extraction/
  evaluation/
reports/
  evaluation/
```

## SQLite schema v1

SQLite lưu dữ liệu có cấu trúc và trace thí nghiệm. Vector lớn không lưu trực tiếp trong SQLite.

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
| `tickers_hint` | TEXT | JSON array |
| `company_names_hint` | TEXT | JSON array |
| `sector_hint` | TEXT | Ngành nếu có |
| `event_keywords` | TEXT | JSON array |
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
| `metadata_json` | TEXT | Metadata dạng JSON |

### `events_gold`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `event_id` | TEXT PRIMARY KEY | ID event |
| `article_id` | TEXT | Bài nguồn |
| `document_label` | TEXT | `HAS_EVENT` hoặc `NO_EVENT` |
| `event_type` | TEXT | Taxonomy chính |
| `event_subtype` | TEXT | Subtype nếu có |
| `impact_sentiment` | TEXT | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED` |
| `event_json` | TEXT | JSON đầy đủ theo schema |
| `teacher_model` | TEXT | Model sinh nhãn |
| `validation_status` | TEXT | `PASS`, `REPAIRED`, `REJECTED` |

### `extraction_runs`

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `run_id` | TEXT PRIMARY KEY | ID lần chạy |
| `article_id` | TEXT | Bài đầu vào |
| `workflow_config` | TEXT | Config LangGraph |
| `model_name` | TEXT | Student LLM |
| `prompt_version` | TEXT | Prompt dùng |
| `retrieval_config` | TEXT | Retrieval config |
| `output_json` | TEXT | Output đã validate |
| `validation_errors` | TEXT | JSON array |
| `latency_ms` | INTEGER | Latency |

## Vector store

### ChromaDB mặc định

Collection đề xuất:

- `financial_news_chunks`
- `financial_news_documents`
- `event_patterns`

Metadata cần lưu cùng vector:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "chunk_id": "cafef_hpg_20260115_001_c03",
  "source": "cafef",
  "published_at": "2026-01-15T08:00:00+07:00",
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hoa Phat"],
  "event_type_hint": "CONTRACT",
  "chunk_level": "paragraph",
  "content_hash": "sha256:..."
}
```

### FAISS baseline

FAISS dùng để so sánh tốc độ và Recall@K. Vì FAISS không quản lý metadata thuận tiện như ChromaDB, cần lưu mapping riêng:

```text
data/vector_store/faiss/index.faiss
data/vector_store/faiss/metadata.jsonl
```

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
  sqlite_path: data/db/finevent_vn.sqlite
  vector_backend: chromadb
  chroma_path: data/vector_store/chroma

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

extraction:
  student_model: qwen_or_llama_8b
  prompt_version: v1
  max_repair_attempts: 2
```

## Nâng cấp sau v1

| Nâng cấp | Khi nào cần |
| --- | --- |
| PostgreSQL + pgvector | Corpus lớn, nhiều user, muốn query SQL + vector chung |
| Elasticsearch/OpenSearch | Cần BM25 mạnh và filter phức tạp |
| Fine-tuned embedding | Retrieval Recall@K thấp dù đã hybrid/rerank |
| Fine-tuned reranker | LLM reasoning rerank quá đắt hoặc chậm |
| FastAPI backend | Demo Streamlit không đủ cho triển khai thật |
