# 07 - Structured Output Viewer

## Mục Tiêu

Model output của project là dữ liệu có cấu trúc, không nên chỉ hiển thị JSON thô.
Structured Output Viewer chuyển prediction/extraction result thành bảng và panel
dễ đọc.

## Input

Viewer nhận một extraction result từ:

- `data/extraction/student_predictions.jsonl`;
- `runs/extraction/{run_id}/result.json`;
- PostgreSQL `extraction_runs`;
- API `GET /admin/outputs/{run_id}`.

## Layout

```text
Output Viewer
├── Article Summary
├── Event Table
├── Event Detail
│   ├── Arguments
│   ├── Evidence
│   ├── Verification
│   └── Raw Event JSON
├── Retrieval Trace
├── Selected Patterns
├── Validation Issues
├── Verification Report
└── Raw JSON
```

## Article Summary

Hiển thị:

- article_id;
- title;
- source;
- url;
- published_at;
- document_label;
- model name;
- prompt version;
- run_id;
- warnings/errors.

## Event Table

Columns:

| Cột | Mô tả |
| --- | --- |
| Event ID | Mã event |
| Ticker | Mã cổ phiếu |
| Company | Tên công ty |
| Event Type | Taxonomy type |
| Subtype | Taxonomy subtype |
| Impact | POSITIVE/NEGATIVE/NEUTRAL/MIXED |
| Confidence | Điểm confidence |
| Evidence | Có/không evidence |
| Verification | supported/unsupported |

Row click mở detail drawer.

## Event Arguments

Arguments hiển thị dạng key-value table:

| Field | Value | Grounded? | Evidence Match |
| --- | --- | --- | --- |

Nếu argument bị verification nullify:

- hiển thị badge `unsupported`;
- show original value nếu verification report có lưu;
- show reason.

## Evidence Viewer

Evidence cần dễ đọc:

- evidence span được highlight;
- source là article hay retrieved context;
- nếu exact match thì badge `exact`;
- nếu fuzzy match thì hiện score;
- nếu unsupported thì hiện warning.

## Retrieval Trace

Bảng:

| Rank | Article | Chunk | Source | Score | BM25 | Dense | Metadata | Text |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |

Cho phép expand text chunk.

## Selected Patterns

Bảng:

| Rank | Pattern ID | Event Type | Subtype | Score | Excerpt |
| --- | --- | --- | --- | ---: | --- |

Detail:

- input excerpt;
- gold output JSON;
- explanation brief.

## Validation Issues

Bảng:

| Severity | Path | Code | Message |
| --- | --- | --- | --- |

Nếu có severity error:

- show red banner;
- link sang schema report.

## Verification Report

Hiển thị cards:

- evidence coverage;
- unsupported field rate;
- unsupported event rate;
- groundedness;
- dropped events;
- unsupported fields.

## Gold Vs Prediction Comparison

Khi có gold label:

- hiển thị gold events và predicted events cạnh nhau;
- match status;
- wrong ticker/type/impact;
- missed events;
- extra events.

V1 có thể chỉ link sang `error_examples.jsonl`. V2 nên có visual diff.

## Raw JSON

Luôn có tab raw JSON:

- pretty print;
- copy;
- download;
- collapse/expand.

Không được thay raw JSON bằng table hoàn toàn, vì debug vẫn cần JSON đầy đủ.

