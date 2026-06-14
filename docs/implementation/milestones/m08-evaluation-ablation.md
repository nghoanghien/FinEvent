# M8: Evaluation and Ablation Study

## Mục tiêu

Đánh giá định lượng toàn bộ hệ thống và chứng minh từng thành phần workflow có giá trị. Đây là phần giúp đồ án đáp ứng yêu cầu bắt buộc về đánh giá độ chính xác.

## Input

```text
data/labels/events_gold.jsonl
runs/extraction/
data/retrieval/retrieval_logs.jsonl
```

## Output

```text
reports/evaluation/metrics_by_run.csv
reports/evaluation/retrieval_metrics.csv
reports/evaluation/hallucination_metrics.csv
reports/evaluation/errors_by_type.csv
reports/evaluation/eval_summary.md
```

## Công nghệ

- pandas.
- numpy.
- scikit-learn.
- matplotlib/seaborn nếu cần biểu đồ.

## Cách triển khai chi tiết

### Bước 1: Tạo dev/test split

Với dữ liệu nhỏ:

- dev: dùng chỉnh prompt/config.
- test: chỉ dùng báo cáo cuối.

Không chỉnh prompt theo test set sau khi đã chốt.

### Bước 2: Retrieval metrics

Tính:

- Recall@K.
- Precision@K.
- MRR.
- nDCG@K.
- latency.

So sánh:

- BM25 only.
- dense only.
- hybrid.
- hybrid + metadata.
- hybrid + rerank.
- hybrid + LLM reasoning rerank.

### Bước 3: Extraction metrics

Tính:

- event detection F1.
- ticker accuracy.
- event type macro-F1.
- event subtype accuracy.
- impact sentiment macro-F1.
- slot-level precision/recall/F1.
- JSON validity rate.

### Bước 4: Hallucination metrics

Tính:

- evidence coverage.
- unsupported field rate.
- unsupported event rate.
- pre/post verification hallucination rate.

### Bước 5: Ablation study

Chạy các cấu hình:

- no retrieval.
- dense only.
- hybrid.
- hybrid + rerank.
- hybrid + patterns.
- hybrid + patterns + verification.

Mục tiêu là chứng minh thành phần nào cải thiện metric nào.

### Bước 6: Error analysis

Phân loại lỗi:

- missed event.
- false positive NO_EVENT.
- wrong ticker.
- wrong event type.
- wrong subtype.
- unsupported argument.
- bad evidence.
- invalid JSON.

Mỗi lỗi nên có ví dụ ngắn để đưa vào báo cáo.

## Kiểm thử

- Test metric function với dữ liệu giả.
- Test multi-event matching.
- Test missing prediction không crash.
- Test macro-F1 xử lý class không xuất hiện.

## Done Criteria

- Có bảng metric cho ít nhất 3 nhóm thí nghiệm.
- Có retrieval metrics.
- Có extraction metrics.
- Có hallucination metrics.
- Có error analysis.
- Có kết luận cấu hình tốt nhất.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| So sánh run không cùng test set | Khóa test split |
| Chỉ báo accuracy | Dùng macro-F1 và per-class F1 |
| Không đo retrieval | Tách retrieval metrics riêng |
| Không có error analysis | Log lỗi theo taxonomy |

