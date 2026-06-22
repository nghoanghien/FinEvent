# Report Charts Visualization

Tài liệu này mô tả cách admin dashboard hiển thị các biểu đồ evaluation. Phần này
bổ sung cho `06-report-viewer.md`: report viewer đọc Markdown/CSV/JSONL, còn file
này tập trung vào chart gallery và metric dashboard.

## Nguồn dữ liệu

Backend chỉ cần đọc artifact đã sinh trong `reports/evaluation/`:

| Artifact | UI nên hiển thị |
| --- | --- |
| `charts_summary.md` | Summary SVG nhẹ, mở nhanh trong Markdown viewer |
| `figures/*.svg` | Biểu đồ metric cơ bản, render trực tiếp trong browser |
| `academic_charts_summary.md` | Trang tổng hợp biểu đồ học thuật |
| `figures_academic/**/*.png` | Chart gallery cho báo cáo/slide |
| `figures_academic/**/*.svg` | Bản SVG nét hơn nếu frontend muốn render vector |

Không nên tính lại chart ở frontend. Frontend chỉ đọc artifact, hiển thị, filter và
link sang CSV/JSONL gốc.

## Màn hình đề xuất

### Overview

Hiển thị các cards:

- Event detection F1.
- Event type macro-F1.
- Slot F1.
- Schema compliance.
- Groundedness score.
- Best retrieval config.
- Top error code.

Cards lấy số từ `metrics_by_run.csv`, `hallucination_metrics.csv`,
`errors_by_type.csv` và `retrieval_metrics.csv`.

### Chart Gallery

Chia tab theo nhóm:

| Tab | Figures |
| --- | --- |
| Dataset | source/date/ticker/event type/polarity/argument coverage |
| Retrieval | metrics comparison, Recall@k, ablation |
| Extraction | overview, per-event-type F1, gold vs pred, errors |
| Verification | grounding, unsupported fields, before/after verification |

Mỗi chart card nên có:

- title;
- last modified time;
- nút mở fullscreen;
- nút tải PNG/SVG;
- link sang artifact nguồn nếu có.

### Report Pairing

Khi người dùng mở một figure, UI nên gợi ý report liên quan:

| Figure group | Report liên quan |
| --- | --- |
| Dataset | `data_quality_summary.md` nếu có, `events_gold.jsonl` |
| Retrieval | `retrieval_metrics.csv`, `retrieval_error_analysis.md` |
| Extraction | `metrics_by_run.csv`, `per_event_type_metrics.csv`, `error_examples.jsonl` |
| Verification | `hallucination_metrics.csv`, `verification_summary.md` |

## API đề xuất

```text
GET /admin/reports/charts
GET /admin/reports/content?path=reports/evaluation/academic_charts_summary.md
GET /admin/reports/content?path=reports/evaluation/figures_academic/final_quality_dashboard.png
GET /admin/reports/table?path=reports/evaluation/metrics_by_run.csv
```

`GET /admin/reports/charts` nên trả về danh sách chart đã group sẵn:

```json
{
  "groups": [
    {
      "key": "extraction",
      "title": "Extraction",
      "charts": [
        {
          "title": "Extraction Overview",
          "png_path": "reports/evaluation/figures_academic/extraction/extraction_overview.png",
          "svg_path": "reports/evaluation/figures_academic/extraction/extraction_overview.svg",
          "source_tables": [
            "reports/evaluation/metrics_by_run.csv"
          ]
        }
      ]
    }
  ]
}
```

## Frontend stack

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Page/layout | Next.js App Router | Route `/admin/reports/charts` |
| Static artifact render | `<img>` / optimized image handling | Hiển thị PNG/SVG đã sinh |
| Interactive metric cards | Recharts hoặc Tremor | Vẽ cards/charts nhỏ từ CSV/API |
| Data table | TanStack Table | Xem metrics CSV bên dưới chart |
| Fullscreen preview | Dialog/sheet component | Phóng to chart khi phân tích |

Với v1, ưu tiên render artifact có sẵn. Recharts chỉ dùng cho các chart nhỏ cần
lọc tương tác, không thay thế pipeline sinh figure học thuật.

## Acceptance Criteria

- UI xem được `charts_summary.md` và `academic_charts_summary.md`.
- UI mở được từng PNG/SVG trong `figures/` và `figures_academic/`.
- Có tab theo nhóm Dataset/Retrieval/Extraction/Verification.
- Có link từ chart sang CSV/JSONL/report liên quan.
- Nếu artifact chưa tồn tại, UI hiển thị hướng dẫn chạy `finevent-evaluate run`.
