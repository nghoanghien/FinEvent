# Data Workflow

## Mục tiêu

Tạo dataset mới về bài báo tài chính doanh nghiệp tiếng Việt, đủ sạch để:

- Làm corpus truy hồi.
- Tạo pattern và AI-generated gold labels.
- Đánh giá hệ thống trích xuất sự kiện.
- Chứng minh tính mới của dữ liệu trong báo cáo SE365.

## Nguồn dữ liệu v1

Ưu tiên báo tài chính Việt Nam công khai:

| Nguồn | Vai trò |
| --- | --- |
| CafeF | Tin doanh nghiệp, cổ phiếu, lãnh đạo, dự án |
| Vietstock | Tin thị trường, doanh nghiệp niêm yết, công bố |
| FireAnt/news công khai | Bổ sung tin theo mã cổ phiếu |
| Website quan hệ nhà đầu tư | Tin chính thức nếu cần đối chiếu |

Không đưa mạng xã hội vào v1 để tránh nhiễu và khó đánh giá.

## Input

Danh sách URL hoặc danh sách ticker cần crawl.

Ví dụ:

```json
{
  "tickers": ["HPG", "VHM", "VCB", "PNJ"],
  "sources": ["cafef", "vietstock"],
  "date_from": "2025-01-01",
  "date_to": "2026-06-13",
  "max_articles": 200
}
```

## Output

File JSONL bài báo thô:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "source": "cafef",
  "url": "https://example.com/news",
  "title": "HPG khởi công dự án mới",
  "published_at": "2026-01-15T08:00:00+07:00",
  "raw_html": "<html>...</html>",
  "raw_text": "Nội dung bài báo...",
  "crawl_time": "2026-06-13T19:00:00+07:00"
}
```

File JSONL sau làm sạch:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "source": "cafef",
  "url": "https://example.com/news",
  "title": "HPG khởi công dự án mới",
  "published_at": "2026-01-15T08:00:00+07:00",
  "text": "HPG khởi công dự án...",
  "preprocessing": {
    "body": {
      "version": "vi_preprocess_v1",
      "tools": {
        "viet_normalizer": "vietnormalizer",
        "domain_normalizer": "finevent_financial_rules"
      }
    }
  },
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hòa Phát"],
  "sector_hints": ["materials_steel"],
  "event_keywords": ["khoi cong", "nha may moi"],
  "event_type_hints": ["EXPANSION"],
  "event_subtype_hints": ["NEW_FACTORY", "NEW_PROJECT"],
  "language": "vi",
  "content_hash": "sha256:...",
  "version": "v1"
}
```

## Công nghệ

- `requests` hoặc `Scrapy` để crawl.
- `BeautifulSoup` để parse HTML.
- `trafilatura` hoặc rule riêng để trích text chính.
- `VietNormalizer` nếu có sẵn để chuẩn hóa text phi chuẩn; fallback rule riêng xử lý
  viết tắt tài chính, số và tiền tệ.
- `pandas` để kiểm tra chất lượng dữ liệu.
- JSONL để lưu dữ liệu tuyến tính, dễ version bằng git/lưu artifact.
- PostgreSQL để lưu metadata có cấu trúc, labels và run trace.
- pgvector/FAISS được build ở workflow RAG preparation, không lưu trực tiếp trong file này.

## Cách hoạt động

1. **Collect URLs**
   - Từ trang danh mục theo ticker hoặc keyword.
   - Keyword gợi ý: `ký hợp đồng`, `trúng thầu`, `phát hành cổ phiếu`, `mở rộng nhà máy`, `bổ nhiệm`, `miễn nhiệm`, `bị phạt`, `kiện tụng`, `M&A`.

2. **Download raw pages**
   - Lưu URL, HTTP status, thời gian crawl.
   - Retry nhẹ nếu lỗi mạng.
   - Không crawl quá nhanh để tránh gây tải cho website.

3. **Extract article content**
   - Tách title, published date, body text.
   - Loại menu, quảng cáo, bài liên quan, bình luận.

4. **Normalize**
   - Chuẩn hóa whitespace.
   - Chuẩn hóa ngày giờ về ISO 8601.
   - Chuẩn hóa encoding Unicode.
   - Mở rộng viết tắt tài chính như `đhcđ`, `hđqt`, `cp`, `ctcp`.
   - Đồng nhất định dạng số và tiền tệ như `1.200,5 tỷ đ` -> `1200.5 tỷ đồng`.
   - Loại bài quá ngắn hoặc không phải tiếng Việt.

   Chi tiết tiền xử lý tiếng Việt:

   - `text` luôn là bản đọc tự nhiên đã normalize, không dùng dấu gạch dưới và không qua
     word segmentation. Đây là trường dùng để hiển thị, validate `evidence_span`, tính
     `content_hash`, sync DB, BM25 và embedding.
   - VietNormalizer là optional dependency. Khi có package, pipeline gọi ở chế độ không
     chuyển số/ngày sang chữ đọc TTS, sau đó rule tài chính của project chuẩn hóa tiếp
     viết tắt, số và tiền tệ để giữ tham số máy đọc được.
   - Mỗi record có `preprocessing.body` và `preprocessing.title` để biết phiên bản
     preprocessing, tool nào đã chạy, tool nào fallback và warning nào phát sinh.
   - M03 và M06 dùng trực tiếp `text` đã normalize. Project không dùng VnCoreNLP để tránh
     thay đổi ranh giới từ và làm nhiễu embedding.

5. **Deduplicate**
   - Dùng `content_hash`.
   - Nếu cùng nội dung xuất hiện ở nhiều URL, giữ bản có metadata tốt nhất.

6. **Ticker/company hinting**
   - Dùng dictionary mapping tên công ty và mã cổ phiếu.
   - Chỉ là hint, không xem là nhãn gold.

7. **Write structured storage**
   - Ghi bài sạch vào `articles_clean.jsonl`.
   - Ghi metadata vào PostgreSQL bảng `articles` và `article_metadata`.
   - Không ghi vector ở bước này.

8. **Sampling for AI labeling**
   - Lấy mẫu cân bằng theo source, ticker, keyword và thời gian.
   - Ưu tiên bài có sự kiện doanh nghiệp rõ ràng.

## AI Labeling Workflow

Mỗi bài được gán một trong hai trạng thái:

- `HAS_EVENT`: có ít nhất một sự kiện doanh nghiệp cụ thể.
- `NO_EVENT`: chỉ là nhận định chung, phân tích thị trường, tin giá, hoặc không có hành động doanh nghiệp rõ.

Nếu `HAS_EVENT`, teacher LLM điền schema trong [event-schema.md](../../schema/event-schema.md).

Quy trình gán nhãn:

1. Teacher LLM tạo nhãn theo schema chuẩn.
2. Hệ thống tự động validate JSON, enum, field bắt buộc và evidence span.
3. Nếu lỗi format/schema, gọi AI repair prompt để sửa cấu trúc mà không thêm thông tin mới.
4. Nếu pass auto validation, nhãn được chấp nhận trực tiếp làm `AI-generated gold label`.
5. Nếu vẫn fail sau retry, lưu vào `events_rejected.jsonl` và không dùng cho evaluation.

Ghi chú: project không có bước kiểm tra thủ công. Vì vậy, `events_gold.jsonl` là ground truth vận hành do AI sinh ra, không phải nhãn chuyên gia.

## Metrics

| Metric | Cách đo | Mục tiêu v1 |
| --- | --- | --- |
| Article count | Số bài sạch | >= 100 |
| Duplicate rate | Bài trùng / tổng bài crawl | < 10% sau lọc |
| Extraction success rate | Bài parse được text / bài crawl thành công | >= 85% |
| Event coverage | Số event type có mẫu | >= 6 nhóm chính |
| AI label count | Số bài có nhãn AI pass auto validation | >= 60 |
| Auto validation pass rate | Nhãn pass validation / tổng nhãn AI sinh | >= 80% |
| NO_EVENT ratio | Tỷ lệ bài không có sự kiện | 10-40% để test lọc nhiễu |

## Failure Cases

| Case | Cách xử lý |
| --- | --- |
| Không lấy được HTML | Lưu status, bỏ qua hoặc retry |
| HTML parse sai | Đánh dấu `parse_failed`, không đưa vào training/eval |
| Bài quá ngắn | Loại nếu text dưới ngưỡng, ví dụ 300 ký tự |
| Nhiều bài copy nhau | Dedup bằng hash và similarity |
| Không rõ ngày đăng | Cho phép `published_at=null`, nhưng ghi warning trong label metadata |

## Artifact

Đề xuất cấu trúc:

```text
data/
  raw/
    articles_raw.jsonl
    html/
  processed/
    articles_clean.jsonl
  labels/
    events_ai_generated.jsonl
    events_gold.jsonl
    events_rejected.jsonl
  db/
    postgres_managed_by_docker
  dictionaries/
    ticker_company_map.csv
    event_keyword_taxonomy.csv
```

Ticker dictionary có hai lớp lưu trữ:

- CSV seed trong `data/dictionaries/ticker_company_map.csv` để review, audit và version.
- PostgreSQL operational store gồm `ticker_companies`, `ticker_company_aliases`, `ticker_dictionary_sync_runs` để API/backend sử dụng lâu dài.

Cập nhật ticker lâu dài nên đi qua API:

```text
PUT /dictionary/tickers/{ticker}
POST /dictionary/tickers/bulk-upsert
```

Vector index và chunk artifact được tạo trong [rag-preparation-workflow.md](rag-preparation-workflow.md):

```text
data/
  processed/
    chunks.jsonl
  vector_store/
    pgvector/
    faiss/
```
