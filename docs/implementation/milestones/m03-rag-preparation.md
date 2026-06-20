# M03: RAG Preparation

## Mục tiêu

Milestone này chuẩn bị corpus cho retrieval và evidence grounding. Đây là bước offline/batch, chạy sau M01 ingestion và sau khi đã có `articles_clean.jsonl`.

M03 tạo:

- `chunks.jsonl`: chunk có cấu trúc, đủ metadata.
- BM25 index: baseline lexical retrieval.
- Embedding artifacts: local hash embedding để smoke test/offline baseline, Cloudflare client để chạy thật.
- Vector store metadata: staging cho pgvector và FAISS baseline.
- PostgreSQL/pgvector schema và command sync.
- Report chất lượng RAG preparation.

## Vai trò trong project

M03 là nền giữa dữ liệu báo chí và các workflow RAG/extraction sau này:

- M04 retrieval/reranking dùng chunks + BM25 + embeddings để lấy context.
- M05 pattern library dùng chunk/evidence để tìm mẫu tương tự.
- M06 online extraction dùng paragraph chunk làm evidence span.
- M08 evaluation dùng BM25/dense/hybrid artifacts để đo Recall@k, MRR, nDCG.

## Input

```text
data/processed/articles_clean.jsonl
configs/default.yaml
```

## Output

```text
data/processed/chunks.jsonl
data/retrieval/bm25_index.pkl
data/retrieval/chunk_embeddings.jsonl
data/retrieval/embedding_cache.jsonl
data/vector_store/manifest.json
data/vector_store/local/metadata.jsonl
data/vector_store/faiss/metadata.jsonl
data/vector_store/faiss/index.faiss        # chỉ có nếu đã cài faiss-cpu + numpy
reports/data/rag_preparation_summary.md
infra/postgres/004_retrieval.sql
```

Các output trong `data/processed`, `data/retrieval`, `data/vector_store`, `reports/data` là artifact chạy batch nên không cần commit.

## Công nghệ

| Thành phần | Công nghệ | Dùng để làm gì |
| --- | --- | --- |
| Chunking | `finevent.rag.chunking` | Tạo 3 cấp document/section/paragraph, giữ metadata ở mọi chunk |
| Lexical retrieval | BM25 tự viết bằng Python stdlib | Baseline keyword search, không phụ thuộc package ngoài |
| Tokenization | `finevent.rag.tokenization` | Normalize tiếng Việt không dấu, tách token phục vụ BM25/hash embedding |
| Offline embedding | `HashEmbeddingClient` | Embedding deterministic để test, demo offline, ablation baseline |
| Production embedding | `CloudflareEmbeddingClient` | Gọi Cloudflare Workers AI khi có account/token |
| Embedding cache | JSONL cache theo `embedding_model + chunk_hash` | Tránh gọi lại embedding nếu text không đổi |
| Vector metadata | JSONL + manifest | Mapping chunk/metadata/embedding cho FAISS/pgvector |
| FAISS baseline | Optional `faiss-cpu` + `numpy` | Nếu cài sẵn thì build `index.faiss`, nếu không thì ghi skipped manifest |
| Database | PostgreSQL + pgvector | Lưu documents/chunks/embeddings cho retrieval lâu dài |
| CLI | `python -m finevent.rag` | Chạy prepare, query BM25, sync PostgreSQL |

## Thiết kế chunk

Mỗi bài tạo 3 cấp:

| Cấp | Mục đích | Nội dung |
| --- | --- | --- |
| `document` | Tìm bài tương tự ở mức toàn cục | title + body rút gọn |
| `section` | Tìm vùng ngữ cảnh | nhóm paragraph theo target/max words và overlap |
| `paragraph` | Lấy evidence cụ thể | từng paragraph hoặc paragraph dài được tách theo câu |

Mỗi chunk có các field chính:

```json
{
  "chunk_id": "cafef_833adef5f3d9_paragraph_0000",
  "article_id": "cafef_833adef5f3d9",
  "chunk_level": "paragraph",
  "chunk_index": 0,
  "text": "...",
  "title": "...",
  "source": "cafef",
  "url": "...",
  "published_at": "2026-01-15T08:00:00+07:00",
  "content_hash": "sha256:...",
  "chunk_hash": "sha256:...",
  "text_word_count": 18,
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hoa Phat Group"],
  "event_keywords": ["khoi cong", "mo rong"],
  "event_type_hints": ["EXPANSION"],
  "event_subtype_hints": ["NEW_FACTORY"],
  "metadata": {
    "representation": "evidence_paragraph",
    "paragraph_index": 0
  }
}
```

Nguyên tắc:

- Không cắt cố định theo token một cách tùy tiện.
- Ưu tiên ranh giới paragraph.
- Paragraph dài mới tách tiếp theo sentence.
- Section có overlap theo paragraph để giảm mất ngữ cảnh.
- Mọi chunk giữ lại ticker hints, company hints, event keyword hints, source/date/title.

## Workflow triển khai

### Bước 1: Build RAG artifacts

Chạy local/offline bằng hash embedding:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.rag prepare `
  --articles-path data\processed\articles_clean.jsonl `
  --chunks-output-path data\processed\chunks.jsonl `
  --retrieval-dir data\retrieval `
  --vector-store-dir data\vector_store `
  --report-path reports\data\rag_preparation_summary.md `
  --embedding-provider hash `
  --embedding-dimension 128
```

Chạy bằng Cloudflare embedding khi đã có token:

```powershell
$env:CLOUDFLARE_ACCOUNT_ID="..."
$env:CLOUDFLARE_API_TOKEN="..."
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.rag prepare `
  --embedding-provider cloudflare `
  --embedding-model "@cf/baai/bge-m3" `
  --embedding-dimension 1024
```

Lưu ý: `embedding_dimension` phải khớp dimension thật của model khi sync vào pgvector/evaluation.

### Bước 2: Smoke query BM25

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.rag query-bm25 `
  --index-path data\retrieval\bm25_index.pkl `
  --query "HPG khoi cong nha may" `
  --top-k 5
```

Kết quả phải trả về chunk liên quan đến bài HPG hoặc các bài có keyword tương ứng.

### Bước 3: Tạo bảng PostgreSQL/pgvector

```powershell
psql $env:POSTGRES_DSN -f infra\postgres\004_retrieval.sql
```

Các bảng chính:

- `financial_news_documents`
- `financial_news_chunks`
- `financial_news_chunk_embeddings`

### Bước 4: Sync PostgreSQL

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.rag sync-postgres `
  --articles-path data\processed\articles_clean.jsonl `
  --chunks-path data\processed\chunks.jsonl `
  --embeddings-path data\retrieval\chunk_embeddings.jsonl
```

Sync này dùng JSONL artifacts làm source và upsert vào PostgreSQL.

## Embedding strategy

M03 không gọi API embedding trong test mặc định vì cần test ổn định, không phụ thuộc mạng và chi phí.

Vì vậy có 2 mode:

- `hash`: deterministic local embedding, dùng để smoke test, BM25/dense pipeline baseline, CI/local.
- `cloudflare`: production embedding, dùng cho corpus thật khi đã có Cloudflare credentials.

Cache key:

```text
embedding_model + chunk_hash
```

Nếu text chunk không đổi, pipeline lấy lại embedding trong `embedding_cache.jsonl`, không gọi lại model.

## FAISS baseline

M03 ghi mapping vào:

```text
data/vector_store/faiss/metadata.jsonl
```

Nếu môi trường đã cài `faiss-cpu` và `numpy`, pipeline tự build:

```text
data/vector_store/faiss/index.faiss
```

Nếu chưa cài, `manifest.json` sẽ ghi:

```json
{
  "faiss_index_status": "skipped_missing_faiss"
}
```

Điều này giúp project hiện tại vẫn chạy nhẹ, nhưng sau này có thể bật FAISS baseline mà không đổi workflow.

## Metrics trong report

`reports/data/rag_preparation_summary.md` gồm:

| Metric | Ý nghĩa |
| --- | --- |
| Clean articles indexed | Số bài sạch được đưa vào corpus |
| Chunks generated | Tổng số chunks |
| Average chunks/article | Mật độ chunk theo bài |
| Embedding success rate | Tỷ lệ chunk có embedding thành công |
| Embedding cache hit rate | Tỷ lệ reuse cache |
| Chunk ticker metadata coverage | Tỷ lệ chunk có ticker hints |
| Chunk event keyword coverage | Tỷ lệ chunk có keyword hints |
| Chunk level distribution | Phân bố document/section/paragraph |
| Source distribution | Số document chunks theo source |

## Kiểm thử

Đã có test:

```text
tests/test_rag_preparation.py
```

Chạy:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests\test_rag_preparation.py
```

Test bao phủ:

- Chunking giữ `article_id`, ticker, event metadata.
- Chunking tạo đủ document/section/paragraph.
- BM25 query trả kết quả liên quan.
- Embedding cache reuse theo chunk hash.
- Full `run_rag_preparation` ghi đủ chunks, embeddings, BM25, vector manifest và report.

## Done Criteria

- Có module `finevent.rag`.
- Có `chunks.jsonl` khi chạy prepare.
- Có BM25 index và query được top K.
- Có embedding artifacts và cache.
- Có vector manifest và metadata cho local/FAISS.
- Có SQL pgvector schema.
- Có CLI sync PostgreSQL.
- Có summary report.
- Có test M03 pass.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Chunk cắt mất evidence | Dùng paragraph-aware split và paragraph overlap |
| Embedding quá tốn chi phí | Cache theo `embedding_model + chunk_hash` |
| Metadata thiếu | Lấy từ article metadata; thiếu thì để list rỗng, không tự bịa |
| BM25 yếu với tiếng Việt có dấu | Tokenizer đã fold dấu; milestone sau có thể thử VnCoreNLP/underthesea |
| FAISS không build | Cài `faiss-cpu` + `numpy`, pipeline sẽ tự build |
| Cloudflare thiếu token | Dùng `hash` mode để test; chỉ dùng `cloudflare` khi có credentials |
