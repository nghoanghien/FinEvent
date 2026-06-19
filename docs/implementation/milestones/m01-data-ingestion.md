# M1: Data Ingestion

## Mục tiêu

Thu thập và làm sạch bài báo tài chính tiếng Việt để tạo corpus mới cho project. Đây là phần chứng minh tính mới của dữ liệu và là nền cho labeling, retrieval, extraction, evaluation.

## Input

```json
{
  "sources": ["cafef", "vietstock"],
  "tickers": ["HPG", "VHM", "VCB", "PNJ"],
  "keywords": ["trúng thầu", "tăng vốn", "bổ nhiệm", "kiện tụng"],
  "date_from": "2025-01-01",
  "date_to": "2026-06-13",
  "max_articles": 200
}
```

## Output

```text
data/raw/articles_raw.jsonl
data/raw/html/
data/processed/articles_clean.jsonl
PostgreSQL database
reports/data/data_quality_summary.md
```

## Implementation hiện tại

Milestone 01 đã có pipeline offline-first để có thể test trước khi bật crawler mạng:

```bash
python -m finevent.ingestion \
  --input-html-dir data/raw/html \
  --raw-output-path data/raw/articles_raw.jsonl \
  --clean-output-path data/processed/articles_clean.jsonl \
  --report-path reports/data/data_quality_summary.md
```

Nếu muốn test nhanh bằng fixture:

```bash
python -m finevent.ingestion \
  --input-html-dir tests/fixtures/html \
  --raw-output-path data/raw/articles_raw.jsonl \
  --clean-output-path data/processed/articles_clean.jsonl \
  --report-path reports/data/data_quality_summary.md \
  --min-text-chars 20
```

Nếu đã chuẩn bị `data/raw/url_candidates.jsonl` và đã cài extra ingestion, có thể tải HTML trước rồi parse:

```bash
python -m finevent.ingestion \
  --download \
  --url-candidates-path data/raw/url_candidates.jsonl \
  --input-html-dir data/raw/html \
  --raw-output-path data/raw/articles_raw.jsonl \
  --clean-output-path data/processed/articles_clean.jsonl \
  --report-path reports/data/data_quality_summary.md
```

Các artifact dữ liệu sinh ra trong `data/raw/*.jsonl`, `data/processed/*.jsonl` và `reports/data/*.md` được ignore khỏi git. Dictionary trong `data/dictionaries/` và schema SQL trong `infra/postgres/` được track.

Pipeline hiện có fallback parser bằng Python stdlib nên vẫn chạy được khi chưa cài dependency ingestion. Khi bắt đầu crawl/parse dữ liệu thật, cài thêm nhóm ingestion:

```bash
uv pip compile pyproject.toml --extra config --extra ingestion -o requirements-ingestion.lock
uv pip sync requirements-ingestion.lock
```

Dictionary metadata không được làm tạm. Milestone này dùng hai file quản trị trong `data/dictionaries/`:

- `ticker_company_map.csv`: seed ticker/company/alias/sector cho các doanh nghiệp Việt Nam thường xuất hiện trong báo tài chính.
- `event_keyword_taxonomy.csv`: keyword trigger được map về `event_type` và `event_subtype` theo event schema.

Với ticker dictionary, CSV chỉ là seed/audit artifact. Bản vận hành lâu dài nằm trong PostgreSQL:

- `ticker_companies`: một dòng cho mỗi ticker.
- `ticker_company_aliases`: nhiều alias cho mỗi ticker, phục vụ match không dấu/có dấu.
- `ticker_dictionary_sync_runs`: log các lần sync/update dictionary.

Schema nằm ở `infra/postgres/002_ticker_dictionary.sql`.

Sau mỗi lần cập nhật dictionary, chạy audit:

```bash
python -m finevent.ingestion.audit_dictionaries --fail-on-error
```

Sau khi apply SQL schema, sync CSV seed vào PostgreSQL:

```bash
python -m finevent.ingestion.sync_ticker_dictionary \
  --csv-path data/dictionaries/ticker_company_map.csv
```

Khi backend API hoạt động, cập nhật ticker qua API thay vì sửa tay trong DB:

```text
GET  /dictionary/tickers?query=HPG
PUT  /dictionary/tickers/{ticker}
POST /dictionary/tickers/bulk-upsert
```

Lưu ý: ticker dictionary hiện là seed list có kiểm soát để phục vụ M1/M2, không được xem là master chính thức toàn thị trường. Trước khi chốt dataset nộp báo cáo, cần refresh/đối chiếu với nguồn chính thức HOSE/HSX, HNX, UPCoM và trang quan hệ nhà đầu tư của doanh nghiệp nếu có đổi tên/chuyển sàn.

## Công nghệ

- `requests` cho trang tĩnh.
- `BeautifulSoup` để parse HTML.
- `trafilatura` để trích nội dung chính nếu phù hợp.
- Playwright nếu trang cần render JavaScript.
- PostgreSQL để lưu metadata có cấu trúc.
- SQLAlchemy + Alembic để quản lý schema/migration.
- JSONL để lưu raw/clean artifacts.

## Cách triển khai chi tiết

### Bước 1: Chọn nguồn và chiến lược crawl

Ưu tiên nguồn công khai, ổn định, có nhiều tin doanh nghiệp:

- CafeF.
- Vietstock.
- FireAnt/news công khai nếu truy cập được.
- Website quan hệ nhà đầu tư nếu cần đối chiếu.

Không đưa mạng xã hội vào v1 vì nhiễu cao và khó đánh giá.

### Bước 2: Collect URL

Tạo script nhận ticker/keyword và sinh danh sách URL ứng viên.

Mỗi URL record cần có:

```json
{
  "url": "...",
  "source": "cafef",
  "ticker_hint": "HPG",
  "keyword_hint": "trúng thầu",
  "discovered_at": "..."
}
```

### Bước 3: Download raw HTML

Lưu raw HTML để debug parser:

```text
data/raw/html/{article_id}.html
```

`articles_raw.jsonl` lưu:

- URL.
- source.
- HTTP status.
- crawl time.
- raw text nếu đã extract nhanh.
- path tới HTML.

### Bước 4: Parse article fields

Tách:

- title.
- published date.
- author nếu có.
- body text.
- source URL.

Các parser nên tách theo source để dễ sửa rule từng website.

### Bước 5: Normalize text

Chuẩn hóa:

- Unicode NFC.
- whitespace.
- ký hiệu tiền tệ, phần trăm, ngày tháng.
- loại menu, quảng cáo, footer, bài liên quan.

Không xóa số liệu tài chính vì chúng là event arguments.

### Bước 6: Deduplicate

Dedup bằng:

- canonical URL.
- `content_hash`.
- title similarity.

Nếu hai bài giống nhau, giữ bản có metadata tốt hơn.

### Bước 7: Extract metadata hints

Tạo hint, không xem là gold:

- `tickers_hint`.
- `company_names_hint`.
- `sector_hints`.
- `event_keywords`.
- `event_type_hints`.
- `event_subtype_hints`.
- `source`.
- `published_at`.

Ticker/company lấy từ dictionary `data/dictionaries/ticker_company_map.csv`.

### Bước 8: Ghi PostgreSQL

Ghi bảng:

- `articles`.
- `article_metadata`.

Vector và chunk chưa tạo ở milestone này.

## Kiểm thử

- Test parser trên 5 URL mỗi source.
- Test bài clean không rỗng và dài hơn ngưỡng tối thiểu.
- Test dedup tạo cùng hash cho nội dung giống nhau.
- Test date parse không crash khi thiếu ngày.

## Metrics

| Metric | Mục tiêu v1 |
| --- | --- |
| Clean article count | >= 100 |
| Parse success rate | >= 85% |
| Duplicate rate after clean | < 10% |
| Metadata coverage | >= 80% có title/source/date hoặc warning |
| Vietnamese text ratio | gần 100% trong clean set |

## Done Criteria

- Có tối thiểu 100 bài sạch.
- Có `articles_clean.jsonl`.
- Có PostgreSQL bảng `articles` và `article_metadata`.
- Có báo cáo `reports/data/data_quality_summary.md`.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Parser lấy nhầm menu | Viết parser theo source |
| Bài quá ngắn | Loại hoặc gắn `parse_warning` |
| Nhiều bài trùng | Dedup bằng hash và similarity |
| Không có ticker | Để hint rỗng, không tự bịa |
