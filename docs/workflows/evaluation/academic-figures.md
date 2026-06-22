# Academic Figures Workflow

File này mô tả lớp biểu đồ học thuật được sinh thêm sau khi chạy M08 evaluation.
Mục tiêu là tạo các figure đủ chỉnh chu để đưa vào báo cáo, slide bảo vệ và UI
admin sau này, thay vì chỉ xem log hoặc bảng CSV.

## Vai trò

Hệ thống hiện có hai lớp trực quan:

| Lớp | Công nghệ | Mục đích |
| --- | --- | --- |
| Lightweight charts | SVG thuần Python trong `finevent.evaluation.charts` | Luôn chạy được, nhúng nhanh vào Markdown và admin report viewer |
| Academic figures | `pandas`, `matplotlib`, `seaborn` trong `finevent.evaluation.academic_figures` | Biểu đồ đẹp hơn cho báo cáo học thuật, slide và phân tích kết quả |

Lớp academic figures không thay thế SVG nhẹ. Hai lớp này phục vụ hai nhu cầu khác
nhau: SVG nhẹ cho quan sát nhanh, academic figures cho phân tích nghiêm túc.

## Lệnh chạy

Mặc định `finevent-evaluate run` sẽ sinh cả SVG nhẹ và academic figures:

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --runs-dir runs/extraction `
  --output-dir reports/evaluation
```

Nếu cần chạy nhanh và chỉ sinh SVG nhẹ:

```powershell
finevent-evaluate run `
  --gold-path data/labels/events_gold.jsonl `
  --runs-dir runs/extraction `
  --output-dir reports/evaluation `
  --skip-academic-figures
```

## Output

```text
reports/evaluation/
  academic_charts_summary.md
  figures_academic/
    final_quality_dashboard.png
    final_quality_dashboard.svg
    dataset/
      articles_by_source.png
      articles_by_date.png
      ticker_frequency_top20.png
      event_type_distribution.png
      polarity_distribution.png
      argument_field_coverage.png
    retrieval/
      retrieval_metrics_comparison.png
      recall_at_k_curve.png
      retrieval_ablation.png
      retrieval_failure_by_event_type.png
    extraction/
      extraction_overview.png
      per_event_type_f1.png
      gold_vs_pred_event_type.png
      error_distribution.png
      schema_error_breakdown.png
    verification/
      grounding_metrics.png
      unsupported_fields.png
      verification_before_after.png
      evidence_coverage_by_config.png
```

Mỗi figure được lưu cả `.png` và `.svg`. Báo cáo/slide nên dùng `.png`; frontend
Next.js sau này có thể ưu tiên `.svg` nếu cần render nét hơn.

## Nhóm biểu đồ

### Dataset

| Figure | Dùng để xem |
| --- | --- |
| `articles_by_source` | Nguồn dữ liệu có bị lệch về một báo không |
| `articles_by_date` | Dữ liệu có đủ mới và trải theo thời gian không |
| `ticker_frequency_top20` | Ticker nào xuất hiện nhiều, có lệch dữ liệu không |
| `event_type_distribution` | Taxonomy event type có bị mất cân bằng không |
| `polarity_distribution` | Chiều hướng tác động positive/negative/neutral có cân bằng không |
| `argument_field_coverage` | Các field trong `event_arguments` xuất hiện ra sao |

### Retrieval

| Figure | Dùng để xem |
| --- | --- |
| `retrieval_metrics_comparison` | Cấu hình retrieval nào tốt hơn theo Recall/MRR/nDCG |
| `recall_at_k_curve` | Recall tăng thế nào khi tăng `k` |
| `retrieval_ablation` | Thành phần hybrid/rerank/reasoning rerank có đóng góp không |
| `retrieval_failure_by_event_type` | Loại sự kiện nào có nguy cơ bị bỏ sót |

### Extraction

| Figure | Dùng để xem |
| --- | --- |
| `extraction_overview` | Event F1, Type F1, Slot F1, JSON valid, Schema valid |
| `per_event_type_f1` | Event type nào yếu nhất |
| `gold_vs_pred_event_type` | Model đang sinh thiếu hay sinh dư event type nào |
| `error_distribution` | Lỗi phổ biến nhất trong toàn batch |
| `schema_error_breakdown` | Lỗi format/schema/field/evidence nào cần xử lý trước |

### Verification

| Figure | Dùng để xem |
| --- | --- |
| `grounding_metrics` | Evidence coverage, unsupported rate, groundedness |
| `unsupported_fields` | Field nào hay bị LLM suy diễn thiếu căn cứ |
| `verification_before_after` | Verification có giảm hallucination không |
| `evidence_coverage_by_config` | Config nào bám evidence tốt hơn |

## Cách đọc trong báo cáo học thuật

Trong báo cáo SE365, các biểu đồ này nên được dùng để chứng minh ba luận điểm:

1. Dữ liệu và gold labels có phân bố rõ ràng, có thể phân tích được.
2. Workflow retrieval/extraction/verification có metric định lượng, không chỉ demo.
3. Các cải tiến workflow thật sự đóng góp vào chất lượng cuối cùng qua ablation.

Khi viết nhận xét, không nên chỉ nói “biểu đồ cho thấy kết quả tốt”. Cần gắn với
metric cụ thể, ví dụ:

- “Hybrid retrieval + reranking có Recall@5 cao hơn dense-only, cho thấy retrieval
  đa giai đoạn giúp giảm miss context.”
- “Event type `LEGAL` có F1 thấp do số mẫu ít và evidence dài, cần bổ sung dữ liệu
  hoặc tăng rule verification.”
- “Unsupported field rate giảm sau verification, chứng minh bước hallucination
  reduction có đóng góp thực nghiệm.”

## Dependency

Academic figures cần optional dependency `evaluation`:

```powershell
python -m pip install -e ".[evaluation]"
```

Nếu dùng Miniconda như project hiện tại, hãy chạy lệnh trên trong đúng conda env
`deep-learning-project`.
