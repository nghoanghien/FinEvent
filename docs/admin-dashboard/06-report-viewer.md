# 06 - Report Viewer

## Mục Tiêu

Report Viewer là nơi xem toàn bộ output phân tích sau khi pipeline chạy xong.
Người dùng không cần mở file bằng editor; UI render Markdown, CSV, JSONL thành
dạng dễ đọc.

## Report Sources

Dashboard đọc file từ:

```text
reports/
  data/
  evaluation/
```

Các file quan trọng:

| File | Viewer |
| --- | --- |
| `reports/evaluation/report_index.md` | Markdown |
| `reports/evaluation/eval_summary.md` | Markdown |
| `reports/evaluation/extraction_batch_summary.md` | Markdown |
| `reports/evaluation/verification_summary.md` | Markdown |
| `reports/evaluation/schema_error_summary.md` | Markdown |
| `reports/evaluation/improvement_recommendations.md` | Markdown |
| `reports/evaluation/retrieval_metrics.csv` | Table |
| `reports/evaluation/per_event_type_metrics.csv` | Table |
| `reports/evaluation/error_examples.jsonl` | JSONL list/detail |
| `reports/data/data_quality_summary.md` | Markdown |
| `reports/data/labeling_summary.md` | Markdown |
| `reports/data/rag_preparation_summary.md` | Markdown |

## Màn Hình Reports

Layout:

- Left panel: danh sách report.
- Main panel: nội dung report.
- Top bar: search, refresh, open raw file, copy path.

Report list group:

- Data reports.
- Retrieval reports.
- Pattern reports.
- Extraction/evaluation reports.
- Raw artifacts.

## Markdown Viewer

Yêu cầu:

- render heading/table/list/code block;
- link nội bộ hoạt động;
- preserve monospace;
- có nút copy path;
- có nút open raw.

Markdown viewer dùng cho:

- report index;
- evaluation summary;
- extraction summary;
- verification summary;
- schema error summary;
- recommendations.

## CSV Viewer

Yêu cầu:

- table sortable;
- filter text;
- column visibility;
- numeric formatting;
- download CSV;
- copy selected row.

CSV viewer dùng cho:

- `metrics_by_run.csv`;
- `retrieval_metrics.csv`;
- `per_event_type_metrics.csv`;
- `errors_by_type.csv`;
- `pattern_metrics.csv`;
- `hallucination_metrics.csv`.

## JSONL Viewer

JSONL thường rất khó đọc nếu render raw. UI cần:

- list rows bên trái;
- detail JSON bên phải;
- filter theo article_id, error_code, event_type;
- copy JSON;
- link sang article/extraction run nếu có.

JSONL viewer dùng cho:

- `error_examples.jsonl`;
- `prediction_details.jsonl`;
- `student_predictions.jsonl`;
- retrieval logs nếu cần.

## Report Cards

Overview của Reports nên có cards:

- latest eval run;
- Event F1;
- Type macro-F1;
- Slot-F1;
- Schema compliance;
- Groundedness;
- best retrieval config;
- top error code.

## API Cần Có

```text
GET /admin/reports
GET /admin/reports/content?path=reports/evaluation/eval_summary.md
GET /admin/reports/table?path=reports/evaluation/metrics_by_run.csv
GET /admin/reports/jsonl?path=reports/evaluation/error_examples.jsonl&limit=50&offset=0
```

Response list:

```json
{
  "reports": [
    {
      "path": "reports/evaluation/eval_summary.md",
      "kind": "markdown",
      "title": "Evaluation Summary",
      "updated_at": "...",
      "size_bytes": 1642
    }
  ]
}
```

## Edge Cases

| Case | UI behavior |
| --- | --- |
| File không tồn tại | Show empty state và gợi ý chạy workflow tương ứng |
| File quá lớn | Load paginated hoặc show warning |
| CSV lỗi parse | Show raw text fallback |
| JSONL có dòng lỗi | Skip dòng lỗi, show parse warning |
| Report cũ hơn artifact | Show timestamp để người dùng biết cần rerun |

