# M06: Online Article Extraction Workflow

## Mục tiêu

M06 xây workflow online từ URL/text/article record đến bảng sự kiện JSON theo schema
FinEvent-VN. Đây là workflow chính dùng cho demo app, API backend và evaluation
end-to-end ở các milestone sau.

Trọng tâm của M06 không phải verification sâu. M06 chịu trách nhiệm điều phối các bước:

```text
input article
-> preprocess + metadata hints
-> query rewriting/decomposition
-> retrieval/reranking
-> pattern selection
-> schema-guided extraction prompt
-> parse/repair/validate JSON cơ bản
-> workflow logs
```

Verification chống hallucination sâu như kiểm tra từng argument với evidence, drop field
không có căn cứ và self-verification bằng LLM nằm ở M07.

## Input

M06 hỗ trợ ba dạng input:

```json
{
  "input_type": "text",
  "title": "HPG khoi cong du an nha may moi",
  "value": "Noi dung bai bao...",
  "source": "manual",
  "url": "",
  "published_at": "2026-01-15T08:00:00+07:00"
}
```

```json
{
  "input_type": "article",
  "article": {
    "article_id": "cafef_833adef5f3d9",
    "title": "HPG khoi cong du an nha may moi",
    "text": "Noi dung bai bao..."
  }
}
```

```json
{
  "input_type": "url",
  "value": "file://.../cafef_sample.html"
}
```

`url` hỗ trợ `file://` để test offline và `http/https` nếu cài dependency `requests`.

## Output

Output public của workflow:

```json
{
  "run_id": "extract_...",
  "article_id": "input_001",
  "document_label": "HAS_EVENT",
  "events": [],
  "retrieval_trace": [],
  "selected_patterns": [],
  "validation_issues": [],
  "workflow_warnings": [],
  "workflow_errors": [],
  "node_traces": [],
  "run_dir": "runs/extraction/extract_..."
}
```

## Công nghệ

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Workflow state | Python dataclass | Lưu article, query plan, contexts, patterns, prompt, raw output, final output và trace |
| Workflow runtime | Sequential runner trong code + optional LangGraph extra | Runner hiện tại test offline ổn định; có dependency `workflow` để nâng lên LangGraph |
| Metadata hints | Module ingestion M01 | Trích ticker/company, event keywords, event type/subtype hints |
| Retrieval | M04 `RetrievalEngine` | Lấy top context bằng BM25 + dense + metadata-aware/rerank config |
| Pattern selection | M05 `PatternStore` | Lấy few-shot patterns theo vector + metadata + diversity |
| Prompting | `build_extraction_prompt` | Ghép schema, taxonomy, contexts, patterns và input article |
| Student model | Deterministic baseline hoặc LangChain model object | Baseline chạy local/test; model thật gọi qua LangChain, không tự viết adapter provider |
| Validation/repair | Schema validation M02 | Parse JSON/fenced JSON, fill field thiếu, validate enum/evidence cơ bản |
| Logging | JSONL + prompt/result files | Mỗi run ghi `prompt.txt`, `result.json`, `trace.jsonl` |
| Storage dài hạn | PostgreSQL migration `006_extraction_runs.sql` | Lưu extraction run và node traces để app/evaluation truy vấn |

## Module đã triển khai

```text
src/finevent/extraction/
  __init__.py
  __main__.py
  cli.py
  models.py
  preprocess.py
  prompting.py
  run_sql.py
  student.py
  validation.py
  workflow.py
```

## Workflow chi tiết

### Bước 1: Preprocess

Node `preprocess` nhận input và tạo clean article object:

- Chuẩn hóa title/text.
- Tạo `article_id` ổn định nếu input chưa có.
- Với URL/file HTML, parse title/body/date/source bằng parser M01.
- Gắn metadata hints:
  - `tickers_hint`
  - `company_names_hint`
  - `sector_hints`
  - `event_keywords`
  - `event_type_hints`
  - `event_subtype_hints`
  - `event_keyword_matches` để map keyword/subtype về đúng event type khi dùng
    multi-event query intent.
- Gắn warning nếu text quá ngắn, không có event keyword hoặc không có ticker/company hint.

### Bước 2: Query plan

Node `query_plan` dùng query decomposition của M04:

- query theo title.
- query theo ticker + event keywords.
- query theo company + event keywords.
- query theo event type/subtype.

Nếu `retrieval_config=multi_event_aware_hybrid`, node này dùng `query_mode=event_intent`.
Khi đó hệ thống vẫn giữ query legacy, rồi bổ sung query riêng cho từng event type
được phát hiện trong bài. Chi tiết strategy:
[`docs/workflows/retrieval/multi-event-aware-retrieval.md`](../../workflows/retrieval/multi-event-aware-retrieval.md).

Output là `query_plan` để trace lại vì sao retrieval chọn context đó.

### Bước 3: Retrieve/rerank

Node `retrieve_rerank` gọi `RetrievalEngine` nếu artifact M03/M04 tồn tại:

```text
data/processed/chunks.jsonl
data/retrieval/bm25_index.pkl
data/retrieval/chunk_embeddings.jsonl
```

Nếu thiếu artifact, workflow không crash mà thêm warning `retrieval_artifacts_missing`
và tiếp tục chạy zero-context. Đây là hành vi cần thiết để debug từng milestone độc lập.

Config mặc định:

```text
metadata_aware_hybrid
```

Có thể đổi sang các config M04 như:

- `bm25_only`
- `dense_only`
- `hybrid`
- `metadata_aware_hybrid`
- `rule_aware_rerank`
- `llm_reasoning_rerank`
- `multi_event_aware_hybrid`

`multi_event_aware_hybrid` dùng adaptive budget trong retrieval engine: 5 context cho
bài single-event, 8 context cho 2 event type và tối đa 10 context cho từ 3 event type.
Tuy nhiên M06 còn có `max_contexts` là lớp cắt cuối sau retrieval. Vì vậy khi chọn
strategy multi-event trên Admin UI hoặc CLI, nên đặt `max_contexts` khoảng `8-10`
nếu muốn giữ đủ context mà engine đã chọn.

### Bước 4: Pattern selection

Node `pattern_selection` gọi M05 `PatternStore` nếu artifact pattern tồn tại:

```text
data/patterns/patterns.jsonl
data/patterns/pattern_embeddings.jsonl
```

Mặc định lấy 3 pattern. Pattern được chọn dựa trên:

- dense similarity.
- ticker/company overlap.
- event type/subtype overlap.
- keyword overlap.
- diversity theo event type.

Nếu `retrieval_config=multi_event_aware_hybrid`, M06 đồng bộ pattern selection với
chunk retrieval:

- pattern query dùng `query_mode=event_intent`;
- `PatternStore.select_patterns_for_queries(...)` nhận query tổng hợp và query riêng
  theo từng event type detected;
- selector `coverage` ưu tiên mỗi event type có pattern đại diện trước khi fill slot
  còn lại bằng score.

`pattern_count` vẫn là giới hạn cuối. Nếu bài có 4 event type nhưng `pattern_count=3`,
few-shot block chỉ cover tối đa 3 event type bằng pattern.

### Bước 5: Prompt extraction

Node `extraction` dựng prompt gồm:

1. System instruction.
2. Output schema rút gọn.
3. Event taxonomy compact.
4. Retrieved contexts top K.
5. Few-shot patterns.
6. Input article.
7. Grounding rules.

Quy tắc quan trọng trong prompt:

- Chỉ trả JSON hợp lệ, không markdown.
- Mỗi event phải có `evidence_span` copy từ bài.
- Không suy diễn field không có evidence.
- `impact_sentiment` chỉ là chiều hướng tác động: `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED`.
- Nếu bài chỉ là nhận định thị trường chung thì trả `NO_EVENT`.

### Bước 6: Student extraction

M06 có hai đường chạy:

| Chế độ | Cách dùng | Mục đích |
| --- | --- | --- |
| Deterministic baseline | Không cần model/API | Test workflow, smoke CLI, demo offline |
| LangChain model object | Truyền model thật vào runner | Gọi student LLM 7B/8B qua LangChain |

Baseline deterministic không phải mô hình chính. Nó chỉ giúp workflow chạy được khi chưa
cấu hình LLM thật. Khi triển khai thật, dùng model 7B/8B qua LangChain model interface.

### Bước 7: Validation/repair cơ bản

Node `validation_repair` xử lý:

- Parse JSON object.
- Parse fenced JSON hoặc text có chứa JSON object.
- Fill các field bắt buộc còn thiếu:
  - `article_id`
  - `document_label`
  - `events`
  - `warnings`
  - `model_info`
  - `event_id`
  - `source_url`
  - `published_at`
  - `confidence`
- Validate bằng schema/taxonomy M02.

Nếu parse fail hoàn toàn, workflow trả:

```json
{
  "document_label": "UNCERTAIN",
  "events": [],
  "warnings": ["model_output_parse_failed"]
}
```

### Bước 8: Logging

Mỗi run tạo thư mục:

```text
runs/extraction/<run_id>/
  prompt.txt
  result.json
  trace.jsonl
```

`trace.jsonl` ghi từng node:

- node name.
- status.
- latency.
- output summary.
- warnings/errors phát sinh ở node đó.

## PostgreSQL schema

Migration:

```text
infra/postgres/006_extraction_runs.sql
```

Bảng:

- `extraction_runs`: lưu config, model, prompt version, final output, validation issues, warnings/errors.
- `extraction_node_traces`: lưu trace từng node cho mỗi run.

Helper:

```text
src/finevent/extraction/run_sql.py
```

## CLI

Run text:

```powershell
$env:PYTHONPATH='src'
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.extraction run-text `
  --title "HPG khoi cong du an nha may moi" `
  --text "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep." `
  --source manual
```

Run article trong `articles_clean.jsonl`:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.extraction run-article `
  --articles-path data\processed\articles_clean.jsonl `
  --article-id cafef_833adef5f3d9
```

Render prompt để debug:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.extraction render-prompt `
  --title "HPG khoi cong du an nha may moi" `
  --text "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep."
```

Các option quan trọng:

```text
--retrieval-config metadata_aware_hybrid
--pattern-count 3
--max-contexts 5
--disable-retrieval
--disable-patterns
--chunks-path ...
--bm25-index-path ...
--retrieval-embeddings-path ...
--patterns-path ...
--pattern-embeddings-path ...
--logs-dir runs/extraction
--output-path output.json
```

## Test

```powershell
$env:PYTHONPATH='src'
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests\test_online_extraction_workflow.py
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m ruff check src\finevent\extraction tests\test_online_extraction_workflow.py
```

Test coverage M06:

- Text có sự kiện chạy được khi tắt retrieval/pattern.
- Text `NO_EVENT` không sinh event nếu thiếu company/ticker grounding.
- Repair được markdown-wrapped JSON.
- Workflow nối được artifact M03 retrieval và M05 pattern trong thư mục tạm.
- Có `retrieval_trace`, `selected_patterns`, `prompt`, `result.json`, `trace.jsonl`.

## Metrics cần đo ở M08

M06 tạo đủ log để M08 tính:

| Metric | Ý nghĩa |
| --- | --- |
| JSON validity rate | Tỷ lệ output parse được |
| Schema compliance rate | Tỷ lệ output đúng enum/field |
| Event detection F1 | Có/không có event |
| Event type macro-F1 | Phân loại event type |
| Event subtype macro-F1 | Phân loại subtype |
| Ticker accuracy | Ticker đúng |
| Slot-level F1 | Argument field đúng |
| Evidence accuracy | Evidence có nằm trong article/context |
| Latency per node | Thời gian từng node |
| Pattern usage rate | Tỷ lệ run có selected patterns |
| Retrieval empty rate | Tỷ lệ run không lấy được context |

## Done Criteria

- Workflow chạy từ text/article/url input đến output JSON.
- Có `query_plan`.
- Có `retrieval_trace` nếu artifact retrieval tồn tại.
- Có `selected_patterns` nếu artifact pattern tồn tại.
- Có prompt extraction versioned.
- Có parse/repair/validation cơ bản.
- Có run logs theo từng node.
- CLI `python -m finevent.extraction` chạy được.
- `pytest` và scoped `ruff` pass.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Thiếu retrieval artifacts | Workflow thêm warning và chạy zero-context |
| Thiếu pattern artifacts | Workflow thêm warning và chạy không few-shot |
| Model trả markdown | Repair JSON object trong fenced block |
| Model trả thiếu field | Fill field bắt buộc rồi validate |
| Text chung chung nhưng có keyword tài chính | Baseline không sinh event nếu thiếu company/ticker grounding |
| Prompt quá dài | Giảm `--max-contexts`, giảm `--pattern-count`, hoặc trim article text |
| Muốn dùng model thật | Truyền LangChain chat model object vào runner thay vì deterministic baseline |
