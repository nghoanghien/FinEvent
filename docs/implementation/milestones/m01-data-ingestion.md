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
data/raw/discovered_urls.jsonl
data/raw/download_log.jsonl
data/raw/html_manifest.jsonl
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

Nếu muốn chạy tự động hơn, dùng discovery từ các trang chuyên mục đã cấu hình sẵn rồi download HTML và parse trong cùng một lệnh:

```bash
python -m finevent.ingestion \
  --discover \
  --input-html-dir data/raw/html \
  --discovered-output-path data/raw/discovered_urls.jsonl \
  --download-log-path data/raw/download_log.jsonl \
  --html-manifest-path data/raw/html_manifest.jsonl \
  --raw-output-path data/raw/articles_raw.jsonl \
  --clean-output-path data/processed/articles_clean.jsonl \
  --report-path reports/data/data_quality_summary.md \
  --max-discovered-urls 80 \
  --max-download-articles 25 \
  --source cafef \
  --source vietstock
```

Logic discovery/download này nằm trong code chính của M01, không còn chỉ nằm trong notebook. Notebook `data-augmentation.ipynb` chỉ dùng để chạy thử trên RAM, quan sát chất lượng parser/cleaning nhanh và xuất JSONL sau khi đã kiểm tra ổn.

Artifact của luồng tự động:

- `data/raw/discovered_urls.jsonl`: danh sách URL ứng viên đã discovery, có `source`, `link_text`, `score`, `seed_url`, `discovered_at`.
- `data/raw/download_log.jsonl`: log từng lượt download, gồm HTTP status, lỗi nếu có và thời điểm download.
- `data/raw/html_manifest.jsonl`: manifest tích lũy map `html_path` sang URL gốc (`source_url`), `source`, `downloaded_at`, `status_code`.
- `data/raw/html/`: HTML snapshot để debug parser và tái lập kết quả.

`download_log.jsonl` là log cho từng run download. `html_manifest.jsonl` là mapping bền vững qua nhiều run; download thành công sẽ upsert theo `html_path`. Khi parse HTML local, M01 dùng manifest để lưu URL gốc vào `article.url`; local snapshot path được lưu riêng ở `raw_html_path`. Nếu HTML không có manifest entry, pipeline fallback về `file://...` như trước và vẫn set `raw_html_path`.

`--reset-html-snapshots` chỉ xóa `*.html` trong `input_html_dir` và file `html_manifest.jsonl` đang chọn. Flag này không xóa PostgreSQL, `articles_clean.jsonl`, reports, chunks, embeddings, patterns hay predictions. Nếu bật reset mà không bật `--discover`/`--download`, M01 sẽ parse thư mục HTML sau khi đã xóa nên raw/clean output có thể rỗng.

Các artifact dữ liệu sinh ra trong `data/raw/*.jsonl`, `data/processed/*.jsonl` và `reports/data/*.md` được ignore khỏi git. Dictionary trong `data/dictionaries/` được track. Schema nền lịch sử nằm trong `infra/postgres/`; migration runtime hiện đi qua Alembic trong `infra/alembic/versions/`.

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

Implementation hiện tại đặt logic này ở `finevent.ingestion.discovery`:

- `default_seed_pages()`: seed các trang chuyên mục tài chính/doanh nghiệp.
- `discover_url_candidates()`: đọc seed page, lọc link cùng domain, loại link chuyên mục/media/static và xếp hạng URL theo keyword/ticker hint.
- `discovered_urls.jsonl`: lưu lại danh sách URL ứng viên để có thể tái lập run hoặc chỉnh tay khi cần.

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

Implementation hiện tại đặt logic này ở `finevent.ingestion.download`:

- `fetch_url_candidates()`: download HTML và giữ trong RAM, dùng cho notebook/debug nhanh.
- `download_url_candidates()`: download HTML và ghi snapshot vào `data/raw/html/`, dùng cho CLI/batch run.
- `download_log.jsonl`: lưu HTTP status, lỗi và kích thước HTML để kiểm tra chất lượng crawl.

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
