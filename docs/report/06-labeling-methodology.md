# 6. Labeling Methodology

## Mục tiêu

Trình bày nguyên tắc gán nhãn dữ liệu và mô tả sơ bộ phần dữ liệu đã gán nhãn.

## Loại nhãn

### Document label

Mỗi bài được gán:

- `HAS_EVENT`: có ít nhất một sự kiện doanh nghiệp cụ thể.
- `NO_EVENT`: không có sự kiện doanh nghiệp cụ thể.

### Event label

Mỗi event gồm:

- ticker.
- company name.
- event type.
- event subtype.
- event summary.
- event arguments.
- impact sentiment.
- evidence span.
- confidence.

## Quy trình gán nhãn

Project dùng teacher LLM để tạo AI-generated gold labels.

Quy trình:

1. Đưa bài clean vào teacher LLM.
2. Teacher LLM sinh JSON theo schema.
3. Hệ thống validate JSON/schema/evidence.
4. Nếu lỗi format/schema, gọi repair prompt.
5. Nếu pass auto validation, chấp nhận làm gold label vận hành.
6. Nếu vẫn fail sau retry, đưa vào rejected set.

Không có bước human review.

## Lý do dùng AI-generated labels

Gán nhãn thủ công cho financial event extraction cần:

- hiểu tài chính.
- hiểu ngữ cảnh doanh nghiệp.
- đọc nhiều bài báo.
- kiểm tra evidence.

Với đồ án v1, dùng teacher LLM giúp:

- giảm chi phí gán nhãn.
- tạo dataset nhanh hơn.
- có đủ dữ liệu để thử nghiệm workflow.
- vẫn kiểm soát chất lượng bằng auto validation.

## Auto validation

Validation kiểm tra:

- JSON parse được.
- enum hợp lệ.
- `event_type`/`event_subtype` đúng taxonomy.
- `impact_sentiment` hợp lệ.
- `evidence_span` nằm trong bài hoặc gần khớp.
- `NO_EVENT` thì `events=[]`.
- `HAS_EVENT` thì có ít nhất một event.

## Label noise

Báo cáo cần ghi rõ:

> Vì nhãn do teacher LLM sinh và không có human review, dataset có thể chứa label noise. Do đó, metric phản ánh mức độ khớp với AI-generated gold labels đã pass auto validation, không tương đương đánh giá bởi chuyên gia tài chính.

Đây là hạn chế được chấp nhận nếu project trình bày theo hướng weak supervision.

## Thống kê nhãn cần báo cáo

| Thống kê | Giá trị |
| --- | --- |
| Số bài gọi teacher LLM | TBD |
| Số bài pass auto validation | TBD |
| Số bài rejected | TBD |
| Auto validation pass rate | TBD |
| Repair rate | TBD |
| `HAS_EVENT` count | TBD |
| `NO_EVENT` count | TBD |

## Phân bố event type

| Event type | Count |
| --- | --- |
| CONTRACT | TBD |
| CAPITAL | TBD |
| LEADERSHIP | TBD |
| EXPANSION | TBD |
| LEGAL_RISK | TBD |
| MA | TBD |
| PARTNERSHIP | TBD |
| OTHER | TBD |

## Ví dụ nhãn

Ví dụ nên đưa vào báo cáo:

```json
{
  "document_label": "HAS_EVENT",
  "events": [
    {
      "ticker": "HPG",
      "event_type": "CONTRACT",
      "event_subtype": "BIDDING_WIN",
      "event_summary": "HPG trúng thầu gói cung cấp thép cho dự án...",
      "event_arguments": {
        "project": "...",
        "contract_value": "..."
      },
      "impact_sentiment": "POSITIVE",
      "evidence_span": "HPG trúng thầu gói...",
      "confidence": 0.82
    }
  ]
}
```

