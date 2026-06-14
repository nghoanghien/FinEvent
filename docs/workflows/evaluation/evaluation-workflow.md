# Evaluation Workflow

## Mục tiêu

Đánh giá định lượng từng bước của hệ thống và toàn bộ pipeline end-to-end. Tài liệu này trả lời yêu cầu SE365: bắt buộc phải có đánh giá độ chính xác của kết quả.

## Input

Gold dataset do AI sinh và pass auto validation:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "text": "Nội dung bài báo...",
  "gold": {
    "document_label": "HAS_EVENT",
    "events": [
      {
        "ticker": "HPG",
        "event_type": "CONTRACT",
        "impact_sentiment": "POSITIVE",
        "evidence_span": "..."
      }
    ]
  }
}
```

Prediction output từ hệ thống:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "prediction": {
    "document_label": "HAS_EVENT",
    "events": []
  },
  "run_info": {
    "model": "qwen-2.5-7b-instruct",
    "config": "hybrid_retrieval_fewshot_v1"
  }
}
```

## Output

Báo cáo đánh giá:

```json
{
  "run_id": "eval_20260613_001",
  "dataset_version": "gold_v1",
  "config": "hybrid_retrieval_fewshot_v1",
  "metrics": {
    "event_detection_f1": 0.78,
    "event_type_macro_f1": 0.66,
    "ticker_accuracy": 0.82,
    "json_validity_rate": 0.98
  },
  "per_event_type": {},
  "error_analysis": []
}
```

## Công nghệ

- Python.
- `pandas` để tổng hợp.
- `scikit-learn` để tính precision/recall/F1.
- `numpy` để tính ranking metrics.
- Optional `matplotlib` hoặc `seaborn` để vẽ biểu đồ báo cáo.
- Script evaluation riêng, không phụ thuộc app demo.

## Các tầng đánh giá

### 1. Data Quality Evaluation

Đánh giá dữ liệu crawl và nhãn AI-generated gold.

| Metric | Ý nghĩa |
| --- | --- |
| Clean article count | Số bài sau làm sạch |
| Duplicate rate | Tỷ lệ bài trùng |
| Label coverage | Số mẫu theo từng event type |
| Auto validation pass rate | Tỷ lệ nhãn AI pass validation |
| AI label rejection rate | Tỷ lệ nhãn bị loại sau retry |
| NO_EVENT ratio | Tỷ lệ bài không có event |

### 2. Retrieval Evaluation

Đánh giá flow [embedding-retrieval-workflow.md](../retrieval/embedding-retrieval-workflow.md).

| Metric | Công thức/Ý nghĩa |
| --- | --- |
| Recall@K | Tỷ lệ AI-generated gold evidence/article xuất hiện trong top K |
| Precision@K | Tỷ lệ top K thật sự liên quan |
| MRR | Trung bình `1/rank` của kết quả đúng đầu tiên |
| nDCG@K | Đánh giá thứ tự ranking với relevance graded |
| Latency | Thời gian truy hồi mỗi bài |

Retrieval ground truth có thể lấy từ:

- evidence article/chunk trong AI-generated gold labels.
- pattern cùng event type/subtype.
- LLM judge relevance cho dev set nếu chưa có nhãn relevance trực tiếp.

Các cấu hình cần so sánh tối thiểu:

| Config | Mục tiêu |
| --- | --- |
| BM25 only | Baseline lexical |
| Dense only | Baseline semantic |
| Hybrid BM25 + dense | Kiểm tra kết hợp keyword/ngữ nghĩa |
| Hybrid + metadata | Đánh giá ticker/company/source/time metadata |
| Hybrid + rule rerank | Đánh giá rule-aware filtering |
| Hybrid + LLM reasoning rerank | Đánh giá reasoning rerank |

### 3. Event Detection Evaluation

Bài toán binary:

- `HAS_EVENT`
- `NO_EVENT`

Metric:

- Accuracy.
- Precision.
- Recall.
- F1.

Ưu tiên F1 vì dữ liệu có thể lệch class.

### 4. Event Extraction Evaluation

Đánh giá từng field:

| Field | Metric |
| --- | --- |
| `ticker` | accuracy |
| `company_name` | exact/normalized match |
| `event_type` | macro-F1, micro-F1 |
| `event_subtype` | accuracy nếu đủ dữ liệu |
| `event_summary` | AI judge rating hoặc semantic similarity |
| `event_arguments` | slot-level precision/recall/F1 |
| `impact_sentiment` | macro-F1 |
| `evidence_span` | exact/partial overlap, AI judge support score |

### 5. Output Quality Evaluation

| Metric | Ý nghĩa |
| --- | --- |
| JSON validity rate | Output parse được JSON |
| Schema compliance rate | Đúng enum và field bắt buộc |
| Hallucination rate | Field không có bằng chứng trong bài |
| Evidence coverage | Tỷ lệ field quan trọng có evidence span |
| Unsupported field rate | Tỷ lệ field bị verification đánh dấu không có căn cứ |
| Groundedness score | Điểm tự kiểm định hoặc judge kiểm tra output có căn cứ |
| Empty failure rate | Đáng lẽ có event nhưng output rỗng |
| Over-extraction rate | Sinh event khi bài `NO_EVENT` |

### 6. End-to-end Evaluation

Đo toàn pipeline từ bài báo đầu vào đến bảng cuối.

Metric chính để báo cáo:

- Event detection F1.
- Event type macro-F1.
- Ticker accuracy.
- Impact sentiment macro-F1.
- JSON validity rate.
- Average latency.
- Average cost per article.

### 7. Hallucination Reduction Evaluation

Đánh giá workflow [verification-hallucination-workflow.md](../extraction/verification-hallucination-workflow.md).

| Metric | Ý nghĩa |
| --- | --- |
| Pre-verification hallucination rate | Tỷ lệ field không có evidence trước verify |
| Post-verification hallucination rate | Tỷ lệ field không có evidence sau verify |
| Dropped unsupported events | Số event bị loại vì không có căn cứ |
| Repair success rate | Tỷ lệ output lỗi được sửa |
| Evidence exact match rate | Evidence span nằm nguyên văn trong bài/context |
| Evidence partial match rate | Evidence khớp một phần hoặc fuzzy match |

Kết luận cần rút ra: verification có giảm hallucination mà không làm giảm quá mạnh recall hay không.

### 8. Ablation Study

Mỗi ablation chỉ tắt một nhóm thành phần để thấy tác động.

| Run | Retrieval | Rerank | Pattern | Verification | Mục tiêu |
| --- | --- | --- | --- | --- | --- |
| A1 | off | off | off | off | Baseline prompting |
| A2 | dense only | off | off | off | Tác động semantic retrieval |
| A3 | hybrid | off | off | off | Tác động BM25 + vector |
| A4 | hybrid | rule | off | off | Tác động rule rerank |
| A5 | hybrid | LLM reasoning | off | off | Tác động reasoning rerank |
| A6 | hybrid | best | on | off | Tác động pattern library |
| A7 | hybrid | best | on | on | Tác động verification |

Metric chính:

- retrieval Recall@K
- event type macro-F1
- slot-level F1
- hallucination rate
- latency/cost

## Matching Rules

Vì một bài có thể nhiều event, cần quy tắc match prediction với AI-generated gold.

Một predicted event match AI-generated gold event nếu:

1. Cùng `ticker` hoặc cùng `company_name` normalized.
2. Cùng `event_type`.
3. Evidence hoặc summary cùng nói về một sự kiện.

Nếu có nhiều match, chọn cặp có score cao nhất.

Score gợi ý:

```text
match_score =
  0.35 * ticker_match
+ 0.35 * event_type_match
+ 0.20 * evidence_overlap
+ 0.10 * argument_overlap
```

## Error Taxonomy

Khi phân tích lỗi, phân loại:

| Error code | Ý nghĩa |
| --- | --- |
| `E_NO_EVENT_FALSE_POSITIVE` | Bài không có event nhưng model sinh event |
| `E_MISSED_EVENT` | Bỏ sót event |
| `E_WRONG_TICKER` | Sai mã cổ phiếu |
| `E_WRONG_EVENT_TYPE` | Sai loại sự kiện |
| `E_WRONG_IMPACT` | Sai chiều hướng tác động |
| `E_UNSUPPORTED_ARGUMENT` | Argument không có trong bài |
| `E_BAD_EVIDENCE` | Evidence không hỗ trợ kết luận |
| `E_INVALID_JSON` | Output không parse được |
| `E_SCHEMA_VIOLATION` | Sai enum hoặc thiếu field |

## Evaluation Split

Với dữ liệu v1 còn nhỏ:

- `dev`: 20-30 bài để chỉnh prompt/config.
- `test`: 40-70 bài chỉ dùng báo cáo cuối.

Không dùng test set để chỉnh prompt sau khi đã chốt.

## Report Template

Mỗi lần chạy thí nghiệm lưu bảng:

| Run | Retrieval | Prompt | Model | Pattern | Event F1 | Type Macro-F1 | JSON Valid | Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | vector only | zero-shot | 8B A | none | | | | |
| R2 | hybrid | few-shot | 8B A | top 3 | | | | |

Với retrieval-specific report, lưu thêm:

| Run | Embedding | Chunking | Retrieval | Rerank | Recall@5 | MRR | nDCG@10 | Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RET1 | Cloudflare | article | dense | none | | | | |
| RET2 | BGE-M3 | hierarchical | hybrid | LLM reasoning | | | | |

## Acceptance Criteria v1

- Có file kết quả metric cho ít nhất 3 cấu hình hệ thống.
- Có bảng per-event-type để thấy class nào yếu.
- Có error analysis tối thiểu 20 lỗi hoặc toàn bộ lỗi nếu ít hơn.
- Có kết luận cấu hình nào tốt nhất và vì sao.

## Limitation: AI-generated Gold Labels

Project không dùng kiểm tra thủ công cho gold labels. Vì vậy, các metric evaluation đo mức độ khớp với nhãn do teacher LLM sinh ra và đã pass auto validation. Đây là ground truth vận hành của project, nhưng có thể chứa label noise.

Khi viết báo cáo, cần ghi rõ:

- Teacher model tạo nhãn để giảm chi phí gán nhãn thủ công.
- Auto validation đảm bảo đúng schema, enum và evidence format.
- Metric phản ánh chất lượng hệ thống so với AI-generated labels, không tương đương đánh giá bởi chuyên gia tài chính.

## Artifact

```text
reports/
  evaluation/
    eval_summary.md
    metrics_by_run.csv
    errors_by_type.csv
    predictions_test.jsonl
```
