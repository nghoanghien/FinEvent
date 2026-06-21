# M08: Evaluation và Ablation Study

## Mục tiêu

Milestone 08 xây dựng tầng đánh giá định lượng cho toàn bộ hệ thống. Đây là
phần bắt buộc để chứng minh workflow không chỉ chạy được demo, mà có thể đo được
độ chính xác, độ ổn định, mức giảm hallucination và đóng góp của từng thành phần
trong pipeline.

M08 tập trung vào 4 câu hỏi:

1. Hệ thống phát hiện đúng bài có sự kiện hay không?
2. Hệ thống trích xuất đúng loại sự kiện, ticker, chiều hướng tác động và slots
   hay không?
3. Tầng verification ở M07 giảm hallucination ra sao?
4. Khi bật/tắt retrieval, pattern library, reranking, verification thì metric
   thay đổi thế nào?

## Vị trí trong pipeline

```text
AI-generated gold labels
prediction outputs / extraction runs
retrieval metrics nếu có
        |
        v
M08 evaluation pipeline
        |
        v
reports/evaluation/
```

## Input

### 1. Gold labels

Mặc định:

```text
data/labels/events_gold.jsonl
```

Mỗi record có thể là dạng đã dùng ở M02:

```json
{
  "article_id": "article_001",
  "label": {
    "article_id": "article_001",
    "document_label": "HAS_EVENT",
    "events": []
  }
}
```

Gold labels của project là AI-generated labels đã pass auto validation. Không có
human review theo quyết định hiện tại của project.

### 2. Prediction records

Có thể đọc từ một file JSONL:

```json
{
  "config_name": "workflow",
  "run_id": "workflow_001",
  "prediction": {
    "article_id": "article_001",
    "document_label": "HAS_EVENT",
    "events": []
  },
  "verification_report": {},
  "hallucination_metrics": {}
}
```

Hoặc đọc trực tiếp từ:

```text
runs/extraction/<run_id>/result.json
```

### 3. Retrieval metrics

Nếu đã chạy M04 retrieval comparison, M08 có thể đọc:

```text
reports/evaluation/retrieval_metrics.csv
```

Retrieval metrics không bắt buộc để chạy extraction evaluation, nhưng sẽ được
nhúng vào `eval_summary.md` nếu file tồn tại.

## Output

M08 sinh các artifact:

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

## Công nghệ và vai trò

| Thành phần | Công nghệ | Dùng để làm gì |
| --- | --- | --- |
| Evaluation core | Python thuần | Tính metric không phụ thuộc bắt buộc vào pandas/sklearn |
| CSV/JSONL writer | `csv`, `json`, helper `finevent.jsonl` | Xuất bảng metric và error examples |
| Event matching | Rule-based greedy matching | Ghép event dự đoán với event gold trong bài nhiều sự kiện |
| Macro/micro F1 | Hàm metric nội bộ | Đo event type và impact sentiment |
| Slot-level metric | Rule-based slot comparison | Đo precision/recall/F1 cho `event_arguments` |
| Hallucination aggregation | M07 `verification_report` | Tổng hợp evidence coverage, unsupported field/event rate |
| CLI | `finevent-evaluate` | Chạy evaluation từ terminal |
| Optional analysis stack | pandas, numpy, scikit-learn, matplotlib, seaborn | Dùng cho notebook/biểu đồ nâng cao về sau |

Package chính:

```text
src/finevent/evaluation/
  loading.py
  metrics.py
  reporting.py
  pipeline.py
  cli.py
```

## Cách triển khai chi tiết

### Bước 1: Load gold labels

Hàm:

```python
load_gold_records(path)
```

Nhiệm vụ:

- đọc `events_gold.jsonl`;
- nhận diện record có `label`, `gold`, hoặc chính record là label;
- chuẩn hóa về schema có `article_id`, `document_label`, `events`;
- trả về mapping `article_id -> GoldRecord`.

### Bước 2: Load predictions

Hàm:

```python
load_prediction_records(...)
```

Hỗ trợ 2 nguồn:

1. `--predictions-path`: file JSONL/JSON chứa prediction của nhiều config.
2. `--runs-dir`: thư mục `runs/extraction`, đọc các file `result.json`.

Mỗi prediction có `config_name`. Trường này dùng để nhóm ablation:

```text
baseline
hybrid
workflow
hybrid_patterns_verification
```

Nếu không có `config_name`, CLI dùng `--default-config-name`.

### Bước 3: Event detection metrics

Bài toán binary:

```text
HAS_EVENT vs NO_EVENT
```

Metric:

- accuracy;
- precision;
- recall;
- F1.

Quy tắc:

```text
gold_has_event = document_label == HAS_EVENT và events không rỗng
pred_has_event = document_label == HAS_EVENT và events không rỗng
```

### Bước 4: Multi-event matching

Vì một bài báo có thể có nhiều event, không thể so sánh theo index. M08 dùng
greedy matching với score:

```text
match_score =
  0.35 * ticker_or_company_match
+ 0.35 * event_type_match
+ 0.20 * evidence_or_summary_overlap
+ 0.10 * argument_overlap
```

Nếu score đủ ngưỡng, event prediction được ghép với event gold tốt nhất chưa
dùng. Cách này cho phép:

- một bài có nhiều event vẫn đánh giá được;
- event sai type nhưng cùng ticker/evidence vẫn được match để ghi lỗi
  `E_WRONG_EVENT_TYPE`;
- event hoàn toàn không liên quan bị tính là extra event.

### Bước 5: Event extraction metrics

Sau khi có event matching, M08 tính:

| Metric | Ý nghĩa |
| --- | --- |
| `event_type_macro_f1` | F1 trung bình theo từng event type |
| `event_type_micro_f1` | F1 gộp toàn bộ event type |
| `impact_sentiment_macro_f1` | F1 trung bình theo chiều hướng tác động |
| `ticker_accuracy` | Tỷ lệ matched event có ticker đúng |
| `event_subtype_accuracy` | Tỷ lệ matched event có subtype đúng |
| `slot_precision` | Slot dự đoán đúng / slot dự đoán |
| `slot_recall` | Slot dự đoán đúng / slot gold |
| `slot_f1` | F1 cho `event_arguments` |
| `json_validity_rate` | Tỷ lệ prediction đọc được JSON |
| `schema_compliance_rate` | Tỷ lệ prediction không có validation error |

### Bước 6: Hallucination metrics

M08 đọc `hallucination_metrics` hoặc `verification_report.metrics` do M07 sinh.

Các trường chính:

| Metric | Ý nghĩa |
| --- | --- |
| `evidence_coverage` | Tỷ lệ evidence span được support |
| `pre_verification_hallucination_rate` | Ước lượng field unsupported trước verification |
| `post_verification_hallucination_rate` | Ước lượng hallucination còn lại sau repair/drop |
| `unsupported_event_rate` | Tỷ lệ event bị drop do không có evidence |
| `groundedness_score` | Điểm groundedness tổng hợp |

Các metric này phục vụ phần báo cáo “verification có giảm hallucination hay không”.

### Bước 7: Error taxonomy

M08 sinh `error_examples.jsonl` và `errors_by_type.csv`.

Các error code:

| Error code | Ý nghĩa |
| --- | --- |
| `E_NO_EVENT_FALSE_POSITIVE` | Bài không có event nhưng model sinh event |
| `E_MISSED_EVENT` | Bỏ sót event trong gold |
| `E_EXTRA_EVENT` | Sinh thêm event không match với gold |
| `E_WRONG_TICKER` | Sai ticker |
| `E_WRONG_EVENT_TYPE` | Sai loại sự kiện |
| `E_WRONG_IMPACT` | Sai chiều hướng tác động |
| `E_UNSUPPORTED_ARGUMENT` | Argument bị M07 đánh dấu không có căn cứ |
| `E_BAD_EVIDENCE` | Evidence không hỗ trợ kết luận |
| `E_INVALID_JSON` | Output không parse được |
| `E_SCHEMA_VIOLATION` | Sai schema hoặc enum |

### Bước 8: Ablation study

M08 không tự train hoặc tự chạy lại toàn bộ extraction. Nó nhận prediction từ
nhiều config khác nhau và so sánh định lượng.

Các config nên chạy trong quá trình làm đồ án:

| Config | Retrieval | Pattern | Verification | Mục tiêu |
| --- | --- | --- | --- | --- |
| `baseline` | off | off | off | Prompting/extractor cơ bản |
| `dense_only` | dense | off | off | Tác động semantic retrieval |
| `hybrid` | BM25 + dense | off | off | Tác động hybrid retrieval |
| `hybrid_rerank` | hybrid + rerank | off | off | Tác động reranking |
| `hybrid_patterns` | hybrid + rerank | on | off | Tác động pattern library |
| `workflow_full` | hybrid + rerank | on | on | Workflow đầy đủ |

Trong báo cáo, cùng một test split phải được dùng cho mọi config.

## CLI

Chạy với prediction JSONL:

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --predictions-path reports/evaluation/predictions_test.jsonl `
  --ignore-runs-dir `
  --output-dir reports/evaluation
```

Chạy trực tiếp từ `runs/extraction`:

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --runs-dir runs/extraction `
  --output-dir reports/evaluation
```

Chạy bằng module:

```powershell
python -m finevent.evaluation run --help
```

## Kiểm thử

Test mới:

```text
tests/test_evaluation_ablation.py
```

Các case đã có:

- event matching dùng ticker, event type, evidence overlap và argument overlap;
- pipeline xuất đủ ablation reports;
- config workflow có metric tốt hơn baseline trong fixture;
- error taxonomy có false positive, missed event, unsupported argument;
- missing prediction không crash và được tính là missed event.

## Done Criteria

- Có module `finevent.evaluation`.
- Có CLI `finevent-evaluate`.
- Có metric event detection, event type, impact sentiment, ticker, subtype, slot.
- Có hallucination metrics từ M07.
- Có error analysis theo taxonomy.
- Có output CSV/JSONL/Markdown trong `reports/evaluation`.
- Có test tự động cho matching, ablation report và missing prediction.
- `pytest` và `ruff` pass.
