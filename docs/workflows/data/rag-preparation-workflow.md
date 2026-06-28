# RAG Preparation Workflow

## Mục tiêu

Workflow này chuẩn bị corpus để retrieval và evidence grounding. Đây là workflow offline/batch, chạy trước khi user nhập bài báo vào app.

Output chính là:

- bài báo sạch
- metadata có cấu trúc
- chunks có chiến lược
- vector index
- BM25 index
- log chất lượng dữ liệu

## Input

```json
{
  "sources": ["cafef", "vietstock"],
  "tickers": ["HPG", "VHM", "VCB", "PNJ"],
  "date_from": "2025-01-01",
  "date_to": "2026-06-13",
  "max_articles": 200
}
```

Input có thể là:

- danh sách URL
- danh sách ticker
- keyword sự kiện
- file bài báo raw đã crawl

## Output

```text
data/raw/articles_raw.jsonl
data/processed/articles_clean.jsonl
data/processed/chunks.jsonl
PostgreSQL database
PostgreSQL pgvector tables/indexes
data/vector_store/faiss/
data/retrieval/bm25_index.pkl
reports/data/data_quality_summary.md
```

## Công nghệ

| Bước | Công nghệ |
| --- | --- |
| Crawl | `requests`, `BeautifulSoup`, `newspaper3k`, Playwright nếu cần |
| Text extraction | `trafilatura` hoặc parser theo source |
| Normalize | Unicode normalization, VietNormalizer optional, financial fallback rules |
| Metadata | dictionary ticker-company, rule-based extractor, optional LLM |
| Chunking | custom Python chunker |
| Embedding | Cloudflare endpoint, BGE-M3, E5, GTE |
| Vector store | PostgreSQL + pgvector mặc định, FAISS baseline offline |
| Structured DB | PostgreSQL |
| BM25 | `rank-bm25` hoặc implementation tương đương |

## Workflow chi tiết

### Bước 1: Collect URLs

Nguồn URL:

- trang tin theo mã cổ phiếu
- trang tìm kiếm theo keyword
- danh mục tin doanh nghiệp
- website quan hệ nhà đầu tư

Keyword gợi ý:

```text
trúng thầu, ký hợp đồng, phát hành cổ phiếu, phát hành trái phiếu,
tăng vốn, giảm vốn, sáp nhập, mua lại, thoái vốn,
bổ nhiệm, miễn nhiệm, khởi công, mở rộng nhà máy,
bị phạt, bị điều tra, kiện tụng, cấp phép, chấp thuận
```

Output:

```json
{
  "url": "https://example.com/news",
  "source": "cafef",
  "ticker_hint": "HPG",
  "discovered_by": "ticker_page",
  "discovered_at": "2026-06-14T10:00:00+07:00"
}
```

### Bước 2: Download raw article

Lưu raw HTML và metadata crawl:

- HTTP status
- crawl time
- final URL sau redirect
- source
- lỗi nếu có

Không parse trực tiếp rồi bỏ HTML. Raw HTML cần giữ lại để debug parser.

### Bước 3: Extract clean text

Trích:

- title
- published date
- author nếu có
- sapo/summary nếu có
- body text

Loại:

- menu
- quảng cáo
- bài liên quan
- comment
- footer
- đoạn lặp lại theo site

Sau khi trích text, M01 lưu một lớp text chính:

- `text`: bản đọc tự nhiên đã normalize bằng Unicode/VietNormalizer/rule tài chính, dùng
  cho evidence span, hiển thị, BM25 và embedding.

M03 giữ `text` trong chunk để trace evidence và dùng chính text này cho BM25/embedding.
Pipeline không dùng VnCoreNLP để tránh biến đổi ranh giới từ thành dạng gạch dưới và làm
nhiễu vector retrieval.

### Bước 4: Normalize Vietnamese text

Chuẩn hóa:

- Unicode NFC.
- whitespace.
- dấu ngoặc, ký tự tiền tệ, phần trăm.
- ngày tháng về ISO nếu parse được.
- bỏ bài quá ngắn.

Không bỏ các số liệu tài chính vì chúng thường là argument quan trọng.

### Bước 5: Metadata extraction

Metadata bắt buộc:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "source": "cafef",
  "url": "...",
  "title": "...",
  "published_at": "2026-01-15T08:00:00+07:00",
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hoa Phat"],
  "event_keywords": ["trúng thầu"],
  "language": "vi",
  "content_hash": "sha256:..."
}
```

Nguồn metadata:

- URL/source.
- title/body.
- dictionary ticker-company.
- event keyword rules.

Ticker chỉ là hint, không phải gold label.

### Bước 6: Deduplicate

Dedup theo:

- canonical URL.
- `content_hash`.
- similarity giữa title + body.

Nếu nhiều source đăng cùng bài, giữ bản có metadata đầy đủ nhất và lưu các URL phụ nếu cần.

### Bước 7: Structure-aware chunking

Không chunk cố định tùy tiện.

Quy tắc:

- Giữ title và sapo trong metadata của mọi chunk.
- Ưu tiên ranh giới paragraph.
- Không tách đôi câu chứa số tiền, ngày tháng, tên dự án.
- Nếu có bullet/table, giữ cùng nhóm nếu liên quan một sự kiện.
- Chunk mục tiêu 300-600 từ tiếng Việt.
- Overlap 50-100 từ khi đoạn dài.

Output chunk:

```json
{
  "chunk_id": "cafef_hpg_20260115_001_p03",
  "article_id": "cafef_hpg_20260115_001",
  "chunk_level": "paragraph",
  "title": "HPG trúng thầu...",
  "text": "Đoạn văn bản...",
  "metadata": {
    "ticker_hint": "HPG",
    "event_keywords": ["trúng thầu"],
    "paragraph_index": 3
  }
}
```

### Bước 8: Hierarchical representations

Tạo 3 cấp retrieval:

| Cấp | Nội dung | Dùng khi |
| --- | --- | --- |
| Document | title + sapo + body rút gọn | tìm bài tương tự |
| Section | nhóm đoạn theo heading/bối cảnh | tìm vùng ngữ cảnh |
| Paragraph chunk | đoạn cụ thể | lấy evidence span |

Khi extraction, ưu tiên paragraph chunk làm evidence, nhưng vẫn đưa document metadata để model hiểu bối cảnh.

### Bước 9: Embedding generation

Mỗi chunk/document được embed.

Yêu cầu:

- cache theo `content_hash`
- lưu `embedding_model`
- lưu `embedding_version`
- log lỗi API
- retry có giới hạn

Không gọi embedding lại nếu text chưa đổi.

### Bước 10: Build indexes

Tạo:

- pgvector tables/indexes cho vector search.
- FAISS index baseline.
- BM25 index cho lexical search.
- PostgreSQL rows cho metadata/chunk/event trace.

### Bước 11: Quality report

Tạo báo cáo:

| Metric | Mục tiêu v1 |
| --- | --- |
| Clean article count | >= 100 |
| Parse success rate | >= 85% |
| Duplicate rate after clean | < 10% |
| Average chunks/article | 2-8 |
| Metadata coverage | >= 80% có source/date/title |
| Embedding success rate | >= 95% |
| pgvector indexed chunks | bằng số chunk embed thành công |

## Acceptance Criteria

Workflow hoàn thành khi:

- Có `articles_clean.jsonl`.
- Có `chunks.jsonl`.
- PostgreSQL có bảng `articles`, `article_metadata`, `chunks`.
- pgvector query được top K theo vector và metadata.
- BM25 query được top K theo keyword.
- Có data quality report.

## Failure Cases

| Case | Cách xử lý |
| --- | --- |
| Parser lấy nhầm menu/quảng cáo | Thêm rule theo source, log `parse_warning` |
| Không parse được ngày | Cho phép `published_at=null`, không loại bài |
| Không tìm được ticker | Để `tickers_hint=[]`, không tự bịa |
| Chunk quá dài | Tách tiếp theo paragraph/sentence |
| Embedding API lỗi | Retry, nếu fail lưu vào queue chạy lại |
| Metadata sai | Xem là hint, không dùng làm gold |
