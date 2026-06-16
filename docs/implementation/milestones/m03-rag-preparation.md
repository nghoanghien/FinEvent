# M3: RAG Preparation

## Mục tiêu

Chuẩn bị corpus cho retrieval: chunking có cấu trúc, embedding, vector index, BM25 index và metadata. Đây là milestone biến dữ liệu bài báo thành nền tảng RAG có thể đánh giá.

## Input

```text
data/processed/articles_clean.jsonl
PostgreSQL database
configs/default.yaml
```

## Output

```text
data/processed/chunks.jsonl
PostgreSQL pgvector tables/indexes
data/vector_store/faiss/
data/retrieval/bm25_index.pkl
reports/data/rag_preparation_summary.md
```

## Công nghệ

- Custom structure-aware chunker.
- Cloudflare embedding hiện có.
- BGE-M3, multilingual E5, GTE multilingual cho thí nghiệm.
- PostgreSQL + pgvector mặc định.
- FAISS baseline.
- BM25 bằng `rank-bm25` hoặc tương đương.
- PostgreSQL bảng `chunks` và embedding tables.

## Cách triển khai chi tiết

### Bước 1: Load clean articles

Đọc `articles_clean.jsonl`, bỏ qua bài:

- text rỗng.
- parse warning nghiêm trọng.
- không phải tiếng Việt.

### Bước 2: Structure-aware chunking

Không chunk cố định theo token một cách tùy tiện.

Quy tắc:

- giữ title/sapo trong metadata.
- ưu tiên ranh giới paragraph.
- không tách câu chứa số tiền, ngày tháng, tên dự án.
- chunk mục tiêu 300-600 từ tiếng Việt.
- overlap 50-100 từ nếu đoạn dài.

### Bước 3: Hierarchical representation

Tạo ba cấp:

- document-level: toàn bài rút gọn.
- section-level: nhóm đoạn theo heading hoặc logic nội dung.
- paragraph-level: evidence cụ thể.

Retrieval sau này có thể tìm bài ở cấp document rồi tìm evidence ở cấp paragraph.

### Bước 4: Generate embeddings

Mỗi text representation được embed và cache theo `content_hash`.

Mỗi embedding record cần log:

- embedding model.
- embedding dimension.
- content hash.
- created at.
- source text ID.

### Bước 5: Build pgvector indexes

Tạo bảng/index embedding:

- `financial_news_documents`.
- `financial_news_chunks`.

Metadata filter cần có:

- article_id.
- chunk_id.
- source.
- published_at.
- tickers_hint.
- event_keywords.
- chunk_level.

Không đồng bộ sang vector database riêng trong v1. PostgreSQL + pgvector là nơi lưu và query vector chính.

### Bước 6: Build FAISS baseline

FAISS dùng cho ablation tốc độ và dense-only retrieval. Vì FAISS không quản lý metadata tốt, lưu mapping:

```text
data/vector_store/faiss/metadata.jsonl
```

### Bước 7: Build BM25 index

BM25 index dùng title + body/chunks. Tokenization tiếng Việt v1 có thể dùng whitespace + normalization đơn giản; nếu có thời gian, thử tokenizer tiếng Việt.

### Bước 8: Write summary report

Report cần có:

- số bài indexed.
- số chunks.
- average chunks/article.
- embedding success rate.
- lỗi embedding.
- thời gian build index.

## Kiểm thử

- Test chunk không mất `article_id`.
- Test chunk có metadata bắt buộc.
- Test pgvector query trả kết quả.
- Test BM25 query bằng keyword sự kiện trả kết quả hợp lý.
- Test cache không gọi embedding lại với cùng hash.

## Metrics

| Metric | Mục tiêu |
| --- | --- |
| Embedding success rate | >= 95% |
| Chunk metadata coverage | >= 95% |
| Average chunks/article | 2-8 với corpus v1 |
| Index query success | 100% với query smoke test |

## Done Criteria

- Có `chunks.jsonl`.
- pgvector query được top K.
- BM25 query được top K.
- FAISS baseline build được nếu config bật.
- Có summary report.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Chunk cắt mất evidence | Dùng paragraph-aware split và overlap |
| Embedding quá tốn chi phí | Cache theo content hash |
| Metadata thiếu | Lấy từ article metadata, nếu thiếu ghi warning |
| BM25 kém với tiếng Việt | Thử tokenizer hoặc keyword normalization |
