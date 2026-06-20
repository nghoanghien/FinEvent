# M02: Event Schema and AI-generated Gold Labels

## Mục tiêu

Milestone này biến event schema trong tài liệu thành một hệ label có thể chạy được bằng code:

- Có taxonomy máy đọc được cho `event_type`, `event_subtype`, `impact_sentiment` và `event_arguments`.
- Có prompt để đưa bài báo sạch cho teacher LLM sinh label.
- Có validator tự động để tách label thành `gold` và `rejected`.
- Chấp nhận label AI nếu pass auto validation, không có bước human review.
- Có schema PostgreSQL để lưu doc-level label và event-level label cho evaluation, pattern library và app.

## Vai trò trong project

M02 tạo lớp dữ liệu trung tâm cho các milestone sau:

- `events_gold.jsonl` là tập label dùng để đo extraction metrics.
- Gold labels là pattern examples cho few-shot/RAG workflow.
- Event type/subtype distribution giúp biết cần crawl thêm nhóm sự kiện nào.
- Evidence span trong label là nền tảng cho hallucination reduction và grounded generation.
- PostgreSQL `events_gold` là bảng dùng cho app, API, evaluation và query phân tích.

## Input

```text
data/processed/articles_clean.jsonl
docs/schema/event-schema.md
data/schema/event_taxonomy_v1.json
data/schema/event_schema_v1.json
```

## Output

```text
data/labels/teacher_prompts.jsonl
data/labels/events_ai_generated.jsonl
data/labels/events_gold.jsonl
data/labels/events_rejected.jsonl
reports/data/labeling_summary.md
infra/postgres/003_event_labels.sql
```

`data/labels/*.jsonl` và `reports/data/*.md` là artifact chạy batch nên được ignore trong Git. Source schema và test fixtures được commit.

## Công nghệ

| Thành phần | Công nghệ | Dùng để làm gì |
| --- | --- | --- |
| Teacher labeling | GPT/Gemini/Claude hoặc LLM mạnh tương đương | Đọc bài báo và sinh nhãn JSON ban đầu |
| Prompt layer | `finevent.labeling.prompting` | Tạo prompt evidence-first theo taxonomy |
| Schema source of truth | `data/schema/event_taxonomy_v1.json` | Lưu event taxonomy, subtype và argument fields cho code |
| JSON schema | `data/schema/event_schema_v1.json` | Mô tả shape output chuẩn của label |
| Auto validator | `finevent.schema.validation` | Kiểm tra enum, subtype, evidence, ticker, consistency |
| Batch storage | JSONL | Lưu raw output, gold, rejected để debug và tái lập thực nghiệm |
| Database storage | PostgreSQL JSONB | Lưu `event_label_documents_gold`, `events_gold`, rejected labels |
| CLI | `python -m finevent.labeling` | Tạo prompt, validate, sync PostgreSQL |

## Label Schema

Doc-level label:

```json
{
  "article_id": "cafef_833adef5f3d9",
  "document_label": "HAS_EVENT",
  "events": [],
  "warnings": [],
  "model_info": {
    "model_name": "teacher_model",
    "prompt_version": "m02_teacher_v1",
    "run_id": "m02_xxx"
  }
}
```

Event-level label:

```json
{
  "event_id": "cafef_833adef5f3d9_e01",
  "ticker": "HPG",
  "company_name": "Hoa Phat Group",
  "event_type": "EXPANSION",
  "event_subtype": "NEW_FACTORY",
  "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
  "event_arguments": {
    "project": "du an nha may moi",
    "location": "khu cong nghiep"
  },
  "impact_sentiment": "POSITIVE",
  "evidence_span": "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.",
  "source_url": "file://...",
  "published_at": "2026-01-15T08:00:00+07:00",
  "confidence": 0.86
}
```

Lưu ý: schema chỉ dùng `impact_sentiment` để biểu diễn chiều hướng tác động. Không gán mức độ ảnh hưởng/severity.

## Workflow chi tiết

### Bước 1: Tạo prompt teacher

Lệnh:

```powershell
$env:PYTHONPATH='src'
python -m finevent.labeling generate-prompts `
  --articles-path data\processed\articles_clean.jsonl `
  --prompt-output-path data\labels\teacher_prompts.jsonl `
  --limit 100
```

Mỗi record trong `teacher_prompts.jsonl` gồm:

- `article_id`
- `prompt_version`
- `taxonomy_version`
- `prompt`
- metadata tóm tắt của bài báo

Prompt yêu cầu teacher LLM:

- Trả về JSON thuần, không Markdown.
- Chỉ gán event nếu có evidence trong bài.
- Nếu không có event cụ thể, trả `document_label=NO_EVENT` và `events=[]`.
- Nếu không chắc subtype, đặt `event_subtype=null`.
- Không sinh severity/mức độ ảnh hưởng.
- Mỗi event phải có `evidence_span`.

### Bước 2: Gọi teacher LLM ngoài pipeline

File output teacher nên có dạng:

```json
{
  "article_id": "cafef_833adef5f3d9",
  "teacher_model": "gemini_or_gpt_teacher",
  "prompt_version": "m02_teacher_v1",
  "generated_at": "2026-06-19T00:00:00+00:00",
  "raw_output": {
    "article_id": "cafef_833adef5f3d9",
    "document_label": "HAS_EVENT",
    "events": [],
    "warnings": [],
    "model_info": {
      "model_name": "gemini_or_gpt_teacher",
      "prompt_version": "m02_teacher_v1",
      "run_id": "m02_xxx"
    }
  }
}
```

`raw_output` có thể là JSON object hoặc string JSON. Validator có hỗ trợ parse fenced JSON dạng ```json.

### Bước 3: Auto validation và tách gold/rejected

Lệnh:

```powershell
$env:PYTHONPATH='src'
python -m finevent.labeling validate `
  --articles-path data\processed\articles_clean.jsonl `
  --teacher-output-path data\labels\teacher_outputs.jsonl `
  --ai-generated-output-path data\labels\events_ai_generated.jsonl `
  --gold-output-path data\labels\events_gold.jsonl `
  --rejected-output-path data\labels\events_rejected.jsonl `
  --report-path reports\data\labeling_summary.md
```

Validator kiểm tra:

- JSON parse được.
- `article_id` khớp với clean article.
- `document_label` thuộc `HAS_EVENT`, `NO_EVENT`, `UNCERTAIN`.
- `document_label` và `events` nhất quán.
- `event_type` thuộc taxonomy.
- `event_subtype` hợp lệ với `event_type`.
- `impact_sentiment` thuộc `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED`.
- `confidence` nằm trong `[0, 1]`.
- `event_arguments` là object.
- `evidence_span` xuất hiện trong title/body hoặc gần khớp với bài gốc.
- `ticker` nằm trong `tickers_hint` hoặc xuất hiện trong bài.

Acceptance policy:

- Pass validation: ghi vào `events_gold.jsonl`.
- Fail validation: ghi vào `events_rejected.jsonl`.
- Không có bước human review. AI sinh sao thì chấp nhận nếu pass validator.

### Bước 4: Repair bằng AI nếu cần

Milestone này chưa gọi API repair trực tiếp, nhưng đã có prompt builder `build_repair_prompt`.

Nguyên tắc repair:

- Chỉ sửa JSON/schema.
- Không thêm thông tin mới.
- Evidence sai thì chọn lại evidence trong bài gốc.
- Subtype sai thì sửa về subtype hợp lệ hoặc `null`.
- Nếu không còn event grounded thì đổi về `NO_EVENT`.

### Bước 5: Sync PostgreSQL

Trước khi sync, chạy SQL:

```powershell
psql $env:POSTGRES_DSN -f infra\postgres\003_event_labels.sql
```

Sau đó sync JSONL:

```powershell
$env:PYTHONPATH='src'
python -m finevent.labeling sync-postgres `
  --gold-path data\labels\events_gold.jsonl `
  --rejected-path data\labels\events_rejected.jsonl
```

Bảng chính:

- `event_labeling_runs`: metadata của lần labeling.
- `event_label_documents_gold`: doc-level label.
- `events_gold`: event-level label dùng cho evaluation/app.
- `event_label_rejections`: label fail validator để debug hoặc repair.

## Metrics trong report

`reports/data/labeling_summary.md` gồm:

| Metric | Ý nghĩa |
| --- | --- |
| AI-generated label records | Số record teacher đã sinh |
| Gold pass count | Số record pass auto validation |
| Rejected count | Số record fail validation |
| Auto validation pass rate | `pass / total` |
| Rejection rate | `rejected / total` |
| Document label distribution | Phân bố `HAS_EVENT`, `NO_EVENT`, `UNCERTAIN` |
| Event type coverage | Số mẫu theo event type |
| Event subtype coverage | Số mẫu theo subtype |
| Impact sentiment distribution | Phân bố chiều hướng tác động |
| Rejection reasons | Lỗi validation phổ biến |

## Kiểm thử

Đã có test source:

```text
tests/test_schema_validation.py
tests/test_labeling_pipeline.py
tests/fixtures/labels/teacher_outputs.jsonl
```

Lệnh khi đã cài pytest:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests\test_schema_validation.py tests\test_labeling_pipeline.py
```

Smoke test không cần pytest:

```powershell
$env:PYTHONPATH='src'
python -m finevent.labeling validate `
  --articles-path data\processed\articles_clean.jsonl `
  --teacher-output-path tests\fixtures\labels\teacher_outputs.jsonl `
  --run-id m02_fixture
```

## Done Criteria

- Có taxonomy JSON cho 16 event type và 87 subtype.
- Có JSON schema output v1.
- Có CLI tạo teacher prompt.
- Có CLI validate teacher output thành AI-generated/gold/rejected.
- Có report summary.
- Có schema PostgreSQL cho gold labels.
- Có test validator và pipeline.
- Khi có dữ liệu thật: ít nhất 60 bài pass auto validation, ít nhất 6 event type, có cả `HAS_EVENT` và `NO_EVENT`.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Teacher bịa ticker | Validator reject nếu ticker không có trong hint/text |
| Evidence không nằm trong bài | Đưa vào rejected và repair bằng AI |
| Subtype sai event type | Sửa subtype về nhóm hợp lệ hoặc `null` |
| Model output Markdown | Parser có hỗ trợ fenced JSON, nhưng prompt vẫn yêu cầu JSON thuần |
| Label quá nghèo argument | Chấp nhận nếu grounded; bổ sung prompt/rerun teacher cho nhóm event đó |
| Class imbalance | Crawl thêm bài theo event type/subtype thiếu |
