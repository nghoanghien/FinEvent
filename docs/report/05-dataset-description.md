# 5. Dataset Description

## Mục tiêu

Trình bày dữ liệu đã thu thập: lấy từ đâu, gồm loại bài nào, thống kê sơ bộ ra sao, và vì sao dữ liệu này phù hợp với bài toán.

## Nguồn dữ liệu

Nguồn v1 đề xuất:

| Nguồn | Vai trò |
| --- | --- |
| CafeF | Tin doanh nghiệp, cổ phiếu, dự án, lãnh đạo |
| Vietstock | Tin công bố, doanh nghiệp niêm yết, thị trường |
| FireAnt/news công khai | Bổ sung tin theo mã cổ phiếu nếu truy cập được |
| Website quan hệ nhà đầu tư | Tin chính thức để đối chiếu nếu cần |

Không đưa mạng xã hội vào v1 để giảm nhiễu và dễ đánh giá.

## Chiến lược thu thập

Thu thập theo:

- mã cổ phiếu.
- keyword sự kiện.
- nguồn báo.
- khoảng thời gian.

Keyword:

```text
trúng thầu, ký hợp đồng, phát hành cổ phiếu, phát hành trái phiếu,
tăng vốn, sáp nhập, mua lại, thoái vốn, bổ nhiệm, miễn nhiệm,
khởi công, mở rộng, bị phạt, bị điều tra, kiện tụng, cấp phép
```

## Các trường dữ liệu raw

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "source": "cafef",
  "url": "...",
  "title": "...",
  "published_at": "...",
  "raw_html_path": "...",
  "raw_text": "...",
  "crawl_time": "..."
}
```

## Các trường dữ liệu clean

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "source": "cafef",
  "url": "...",
  "title": "...",
  "published_at": "...",
  "text": "...",
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hoa Phat"],
  "event_keywords": ["trúng thầu"],
  "language": "vi",
  "content_hash": "sha256:..."
}
```

## Thống kê cần đưa vào báo cáo

Điền số liệu thật sau khi crawl:

| Thống kê | Giá trị |
| --- | --- |
| Số bài raw crawl được | TBD |
| Số bài clean sau lọc | TBD |
| Số nguồn dữ liệu | TBD |
| Khoảng thời gian | TBD |
| Số ticker xuất hiện | TBD |
| Số bài có ticker hint | TBD |
| Số bài có event keyword | TBD |
| Duplicate rate | TBD |
| Parse success rate | TBD |

## Phân bố theo nguồn

| Source | Raw count | Clean count | Parse success |
| --- | --- | --- | --- |
| CafeF | TBD | TBD | TBD |
| Vietstock | TBD | TBD | TBD |
| Khác | TBD | TBD | TBD |

## Phân bố theo event keyword

| Keyword group | Count |
| --- | --- |
| Contract / bidding | TBD |
| Capital / issuance | TBD |
| Leadership | TBD |
| Expansion | TBD |
| Legal risk | TBD |
| M&A / partnership | TBD |

## Chất lượng dữ liệu

Cần báo cáo:

- tỷ lệ bài parse lỗi.
- tỷ lệ bài quá ngắn bị loại.
- tỷ lệ duplicate.
- tỷ lệ thiếu ngày đăng.
- tỷ lệ thiếu ticker hint.

## Hạn chế dữ liệu

Các hạn chế nên ghi thẳng:

- Dataset v1 còn nhỏ.
- Nhãn được sinh bởi AI, không phải chuyên gia tài chính.
- Nguồn báo có thể có thiên lệch.
- Một số bài có thể là tin tổng hợp nhiều sự kiện.
- Ticker không phải lúc nào cũng xuất hiện trực tiếp.

