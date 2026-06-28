# M07: Verification và Hallucination Reduction

## Mục tiêu

Milestone 07 bổ sung một tầng kiểm định sau khi mô hình sinh `draft_output` và trước
khi hệ thống chấp nhận kết quả cuối cùng. Mục tiêu là biến hệ thống từ kiểu "LLM
sinh gì thì dùng nấy" thành workflow trích xuất có căn cứ, trong đó mỗi event và
argument quan trọng đều phải được kiểm tra lại với evidence trong bài báo hoặc
context truy hồi.

M07 không thay thế M06. M06 chịu trách nhiệm điều phối extraction, còn M07 chịu
trách nhiệm quyết định output nào đủ căn cứ để trở thành `final_output`.

## Vị trí trong pipeline

```text
article input
  -> preprocess
  -> retrieval/reranking
  -> pattern selection
  -> extraction model
  -> validation/repair
  -> verification/hallucination reduction   <-- M07
  -> final output + logs + metrics
```

## Input

```json
{
  "draft_output": {
    "article_id": "manual_contract_001",
    "document_label": "HAS_EVENT",
    "events": []
  },
  "article": {
    "article_id": "manual_contract_001",
    "title": "...",
    "text": "..."
  },
  "retrieved_contexts": [],
  "taxonomy": "data/schema/event_taxonomy_v1.json"
}
```

## Output

```json
{
  "verified_output": {
    "article_id": "manual_contract_001",
    "document_label": "HAS_EVENT",
    "events": []
  },
  "verification_report": {
    "schema_valid_before_verification": true,
    "schema_valid_after_verification": true,
    "dropped_events": [],
    "unsupported_fields": [],
    "metrics": {
      "evidence_coverage": 1.0,
      "unsupported_field_rate": 0.0,
      "unsupported_event_rate": 0.0,
      "groundedness_score": 1.0
    }
  }
}
```

## Công nghệ và vai trò

| Thành phần | Công nghệ | Dùng để làm gì |
| --- | --- | --- |
| Schema validation | Python dataclass + validator nội bộ | Kiểm tra output có đúng event schema, enum và taxonomy không |
| Evidence matching | `difflib.SequenceMatcher`, exact match, fuzzy match | Kiểm tra `evidence_span` có xuất hiện hoặc gần khớp với bài báo/context không |
| Text normalization | `finevent.ingestion.text.normalize_text`, Unicode folding | So khớp tiếng Việt ổn định hơn khi có khác biệt dấu, khoảng trắng, HTML entity |
| Taxonomy consistency | `data/schema/event_taxonomy_v1.json` | Kiểm tra `event_type`, `event_subtype`, argument và chiều hướng tác động có hợp lý không |
| Repair policy | Rule-based repair | Drop event không có evidence, set `null` cho argument không grounded, bỏ field ngoài schema |
| Workflow orchestration | Node `verification` trong `finevent.extraction.workflow` | Chạy verification như một bước chính thức của workflow, có trace và latency riêng |
| Logging | JSON artifact trong `runs/extraction/<run_id>/` | Lưu `draft_output`, `verified_output`, `verification_report` để debug và báo cáo |
| Database | PostgreSQL JSONB columns | Lưu draft, final output, verification report và hallucination metrics theo `run_id` |
| Testing | `pytest` | Test drop event, null argument, strip field ngoài schema và tích hợp workflow |

## Các bước triển khai

### Bước 1: Giữ lại validation/repair ở M06

M06 đã có `validate_or_repair_extraction_output()` để xử lý:

- parse JSON hoặc JSON bọc trong Markdown;
- tự điền một số field bắt buộc còn thiếu;
- kiểm tra schema/taxonomy cơ bản;
- tạo `draft_output`.

M07 chạy sau bước này, không xử lý lại toàn bộ parsing từ đầu. Lý do là hệ thống
cần tách rõ:

- `validation_repair`: output có đúng cấu trúc JSON/schema không;
- `verification`: nội dung trong output có căn cứ hay không.

### Bước 2: Thêm module verification độc lập

Module chính:

```text
src/finevent/extraction/verification.py
```

Các hàm/lớp quan trọng:

| API | Vai trò |
| --- | --- |
| `VerificationConfig` | Cấu hình threshold và policy verification |
| `verify_extraction_output()` | Nhận draft output và trả về verified output + report |
| `find_evidence_support()` | Tìm support cho một evidence span trong article/context |
| `build_self_verification_prompt()` | Prompt mẫu cho thí nghiệm self-verification bằng LLM về sau |

Thiết kế này giúp M07 có thể test độc lập, đồng thời vẫn được gọi từ workflow
online.

### Bước 3: Evidence span check

Mỗi event phải có `evidence_span`. Hệ thống kiểm tra theo thứ tự:

1. exact match trong bài báo gốc;
2. fuzzy match trong bài báo gốc;
3. exact/fuzzy match trong retrieved contexts;
4. nếu không tìm thấy support thì event bị đánh dấu unsupported.

Policy mặc định:

```text
event không có evidence -> drop event
```

Nếu sau khi drop không còn event nào, hệ thống đổi `document_label` thành
`NO_EVENT` để tránh giữ một document label mâu thuẫn.

### Bước 4: Argument grounding

Với mỗi `event_arguments`, hệ thống kiểm tra value có xuất hiện trong evidence,
bài báo hoặc context không. Ví dụ:

| Event type | Argument cần kiểm tra |
| --- | --- |
| `CONTRACT` | `partner`, `project`, `product`, `package_name`, `contract_value` |
| `CAPITAL` | `share_volume`, `issue_price`, `capital_before`, `capital_after`, `bond_value` |
| `LEADERSHIP` | `person`, `role`, `action` |
| `LEGAL_RISK` | `legal_authority`, `violation`, `case_name`, `penalty_value` |
| `EXPANSION` | `project`, `location`, `investment_value`, `capacity`, `market` |

Policy mặc định:

```text
argument không grounded -> set null
```

Không dùng verification để tự thêm thông tin mới. Nếu model không đưa ra value
hoặc value không có căn cứ, hệ thống chỉ được bỏ/null value đó.

### Bước 5: Taxonomy consistency

Hệ thống kiểm tra thêm tính nhất quán giữa:

- `event_type`;
- `event_subtype`;
- nhóm argument cốt lõi;
- `impact_sentiment`.

Ví dụ:

- `CONTRACT` nhưng không có `partner`, `project`, `product`, `package_name` hoặc
  `contract_value` thì hạ confidence và thêm warning.
- `LEADERSHIP` nhưng không có `person`, `role` hoặc `action` thì thêm warning.
- `LEGAL_RISK` nhưng `impact_sentiment=POSITIVE` thì thêm warning vì đây là tổ
  hợp cần bằng chứng rất mạnh.
- subtype không thuộc event type thì set `event_subtype=null`.

Lưu ý: project chỉ dùng `impact_sentiment` để biểu diễn chiều hướng tác động,
không dùng mức độ ảnh hưởng/severity.

### Bước 6: Strip field ngoài schema

Để tránh output trôi schema, verifier bỏ các field không thuộc schema chuẩn.
Ví dụ field cũ như `impact_severity` sẽ bị loại bỏ nếu xuất hiện ở top-level
hoặc trong từng event.

Việc này giúp output cuối cùng nhất quán với tài liệu event schema và dễ đưa vào
evaluation/app.

### Bước 7: Hallucination metrics

M07 sinh các metric sau trong `verification_report.metrics`:

| Metric | Ý nghĩa |
| --- | --- |
| `evidence_coverage` | Tỷ lệ event có evidence được support |
| `unsupported_field_rate` | Tỷ lệ field được kiểm tra nhưng không grounded |
| `unsupported_event_rate` | Tỷ lệ event draft bị drop do không có căn cứ |
| `verified_event_retention_rate` | Tỷ lệ event còn lại sau verification |
| `schema_repair_count` | Số thao tác repair/strip/set-null đã thực hiện |
| `repair_success_rate` | Tỷ lệ repair thành công ở tầng rule-based hiện tại |
| `groundedness_score` | Điểm groundedness tổng hợp từ field checks |

Những metric này sẽ được M08 dùng để báo cáo pre/post verification hallucination
rate và chạy ablation study.

### Bước 8: Gắn vào online workflow

`run_online_extraction_workflow()` hiện có thêm node:

```text
verification
```

Node này nhận `state.draft_output`, sinh:

- `state.final_output`;
- `state.verification_report`;
- `state.hallucination_metrics`.

Public result cũng trả thêm:

```json
{
  "verification_report": {},
  "hallucination_metrics": {}
}
```

### Bước 9: Logging artifact

Mỗi run có thêm các file:

```text
runs/extraction/<run_id>/
  prompt.txt
  draft_output.json
  verified_output.json
  verification_report.json
  result.json
  trace.jsonl
```

`result.json` là bản tổng hợp để app hoặc evaluation đọc nhanh. Các file riêng
giúp debug từng tầng của workflow.

### Bước 10: Database sync

PostgreSQL được mở rộng bằng migration:

```text
infra/postgres/007_verification_reports.sql
```

Các cột mới trong `extraction_runs`:

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `draft_output` | JSONB | Output sau validation/repair, trước verification |
| `verification_report` | JSONB | Báo cáo field/event checks, repairs, warnings |
| `hallucination_metrics` | JSONB | Metric hallucination reduction theo run |

Các cột này giúp M08 đọc trực tiếp từ DB để tính metric theo experiment run.

## CLI

Workflow extraction mặc định bật verification.

Ví dụ:

```powershell
finevent-extract run-text `
  --title "HPG trúng thầu gói thầu xây dựng nhà máy" `
  --text "..." `
  --disable-retrieval
```

Chạy ablation không verification:

```powershell
finevent-extract run-text `
  --title "..." `
  --text "..." `
  --disable-verification
```

Tùy chỉnh threshold:

```powershell
finevent-extract run-text `
  --title "..." `
  --text "..." `
  --evidence-match-threshold 0.86 `
  --argument-match-threshold 0.80
```

## Kiểm thử

Test mới:

```text
tests/test_verification_hallucination.py
```

Các case đã có:

- event không có evidence bị drop;
- argument không grounded bị set `null`;
- field ngoài schema bị strip;
- online workflow chạy node `verification` và ghi artifact;
- self-verification prompt bắt buộc chỉ dựa trên article/context và trả JSON.

## Done Criteria

- Có module verification chạy độc lập.
- Online workflow có node `verification`.
- Final output không giữ event thiếu evidence.
- Argument không grounded bị `null` hoặc drop theo policy.
- Field ngoài schema bị loại bỏ.
- `verification_report` và `hallucination_metrics` có trong public result.
- Log artifact có `draft_output.json`, `verified_output.json`,
  `verification_report.json`.
- DB có cột lưu draft/report/metrics để phục vụ M08.
- Test M07 và test workflow liên quan pass.
