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
data/db/finevent_vn.sqlite
reports/data/data_quality_summary.md
```

## Công nghệ

- `requests` cho trang tĩnh.
- `BeautifulSoup` để parse HTML.
- `trafilatura` để trích nội dung chính nếu phù hợp.
- Playwright nếu trang cần render JavaScript.
- SQLite để lưu metadata có cấu trúc.
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
- `event_keywords`.
- `source`.
- `published_at`.

Ticker/company lấy từ dictionary `data/dictionaries/ticker_company_map.csv`.

### Bước 8: Ghi SQLite

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
- Có SQLite bảng `articles` và `article_metadata`.
- Có báo cáo `reports/data/data_quality_summary.md`.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Parser lấy nhầm menu | Viết parser theo source |
| Bài quá ngắn | Loại hoặc gắn `parse_warning` |
| Nhiều bài trùng | Dedup bằng hash và similarity |
| Không có ticker | Để hint rỗng, không tự bịa |

