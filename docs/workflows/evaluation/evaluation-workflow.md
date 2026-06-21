# Evaluation Workflow

## Mục tiêu

Workflow này đánh giá định lượng toàn bộ pipeline trích xuất sự kiện tài chính.
Nó trả lời yêu cầu học thuật quan trọng của đề tài: phải có đánh giá độ chính
xác, có so sánh nhiều cấu hình, có error analysis và có ablation study để chứng
minh từng thành phần workflow tạo ra giá trị.

## Input

### Gold labels

```json
{
  "article_id": "cafef_hpg_001",
  "label": {
    "document_label": "HAS_EVENT",
    "events": [
      {
        "ticker": "HPG",
        "event_type": "CONTRACT",
        "impact_sentiment": "POSITIVE",
        "event_arguments": {},
        "evidence_span": "..."
      }
    ]
  }
}
```

### Prediction records

```json
{
  "config_name": "workflow_full",
  "run_id": "extract_001",
  "prediction": {
    "article_id": "cafef_hpg_001",
    "document_label": "HAS_EVENT",
    "events": []
  },
  "verification_report": {},
  "hallucination_metrics": {}
}
```

## Output

```text
reports/evaluation/
  metrics_by_run.csv
  per_event_type_metrics.csv
  hallucination_metrics.csv
  errors_by_type.csv
  error_examples.jsonl
  prediction_details.jsonl
  eval_summary.md
```

## Công nghệ

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Loader | `finevent.evaluation.loading` | Đọc gold labels, prediction JSONL, extraction run artifacts |
| Metrics | `finevent.evaluation.metrics` | Tính event detection F1, macro-F1, slot-F1, error taxonomy |
| Report writer | `finevent.evaluation.reporting` | Xuất CSV, JSONL, Markdown summary |
| Pipeline | `finevent.evaluation.pipeline` | Chạy end-to-end evaluation và ablation aggregation |
| CLI | `finevent-evaluate` | Chạy workflow từ terminal |
| Optional notebook stack | pandas/numpy/sklearn/matplotlib/seaborn | Phân tích nâng cao, vẽ biểu đồ báo cáo |

## Quy trình

### 1. Chuẩn bị test split

Tạo test split cố định từ AI-generated gold labels. Sau khi chốt test set, không
được chỉnh prompt/config theo test set nữa.

Khuyến nghị:

```text
dev: dùng chỉnh prompt, threshold, workflow policy
test: chỉ dùng báo cáo cuối
```

### 2. Chạy các config cần so sánh

Ví dụ các config ablation:

| Config | Ý nghĩa |
| --- | --- |
| `baseline` | Không retrieval, không pattern, không verification |
| `dense_only` | Chỉ semantic retrieval |
| `hybrid` | BM25 + dense retrieval |
| `hybrid_rerank` | Hybrid + reranking |
| `hybrid_patterns` | Hybrid + pattern library |
| `workflow_full` | Retrieval + rerank + patterns + verification |

Mỗi prediction record cần có `config_name` để M08 nhóm metric.

### 3. Event matching

Mỗi bài báo có thể có nhiều event. Workflow không so sánh theo thứ tự event mà
dùng greedy matching:

```text
0.35 ticker/company
0.35 event type
0.20 evidence/summary overlap
0.10 argument overlap
```

Cách này giúp đánh giá đúng hơn trong các trường hợp:

- model sinh đúng event nhưng đổi thứ tự;
- model sai type nhưng vẫn cùng ticker/evidence;
- model sinh thêm event không có trong gold.

### 4. Extraction metrics

Các metric chính:

| Metric | Ý nghĩa |
| --- | --- |
| `event_detection_f1` | F1 cho bài toán HAS_EVENT/NO_EVENT |
| `event_type_macro_f1` | F1 trung bình theo event type |
| `impact_sentiment_macro_f1` | F1 theo chiều hướng tác động |
| `ticker_accuracy` | Tỷ lệ ticker đúng trên matched event |
| `event_subtype_accuracy` | Tỷ lệ subtype đúng trên matched event |
| `slot_f1` | F1 cho `event_arguments` |
| `json_validity_rate` | Tỷ lệ output parse được JSON |
| `schema_compliance_rate` | Tỷ lệ output không có schema error |

### 5. Hallucination metrics

Workflow đọc metrics từ M07:

| Metric | Ý nghĩa |
| --- | --- |
| `evidence_coverage` | Tỷ lệ evidence được support |
| `pre_verification_hallucination_rate` | Tỷ lệ field unsupported trước verification |
| `post_verification_hallucination_rate` | Tỷ lệ hallucination còn lại sau verification |
| `unsupported_event_rate` | Tỷ lệ event bị drop do thiếu evidence |
| `groundedness_score` | Điểm groundedness tổng hợp |

### 6. Error analysis

Workflow xuất:

```text
errors_by_type.csv
error_examples.jsonl
```

Các nhóm lỗi chính:

| Error code | Ý nghĩa |
| --- | --- |
| `E_NO_EVENT_FALSE_POSITIVE` | Sinh event cho bài không có event |
| `E_MISSED_EVENT` | Bỏ sót event |
| `E_EXTRA_EVENT` | Sinh thêm event |
| `E_WRONG_TICKER` | Sai ticker |
| `E_WRONG_EVENT_TYPE` | Sai loại sự kiện |
| `E_WRONG_IMPACT` | Sai chiều hướng tác động |
| `E_UNSUPPORTED_ARGUMENT` | Argument không có căn cứ |
| `E_BAD_EVIDENCE` | Evidence không hỗ trợ kết luận |
| `E_INVALID_JSON` | Output không parse được |
| `E_SCHEMA_VIOLATION` | Output sai schema |

### 7. Summary report

`eval_summary.md` tổng hợp:

- số config đã đánh giá;
- config tốt nhất;
- bảng metric theo config;
- hallucination metrics;
- error distribution;
- retrieval metrics nếu có.

Config tốt nhất được chọn theo thứ tự ưu tiên:

```text
event_type_macro_f1
slot_f1
groundedness_score
event_detection_f1
```

## Lệnh chạy

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --predictions-path reports/evaluation/predictions_test.jsonl `
  --ignore-runs-dir `
  --output-dir reports/evaluation
```

Hoặc đọc extraction run artifacts:

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --runs-dir runs/extraction `
  --output-dir reports/evaluation
```

## Acceptance Criteria

- Chạy được bằng CLI.
- Xuất đủ `metrics_by_run.csv`, `per_event_type_metrics.csv`,
  `hallucination_metrics.csv`, `errors_by_type.csv`, `error_examples.jsonl`,
  `eval_summary.md`.
- Có metric extraction, hallucination và error analysis.
- Hỗ trợ nhiều config để làm ablation.
- Missing prediction không làm workflow crash.
- Evaluation dựa trên AI-generated gold labels và ghi rõ giới hạn này trong báo cáo.
