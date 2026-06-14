# Verification and Hallucination Reduction Workflow

## Mục tiêu

Workflow này kiểm tra output của LLM trước khi chấp nhận làm kết quả cuối. Mục tiêu là giảm hallucination và đảm bảo bảng sự kiện có bằng chứng.

Workflow này chạy sau extraction và trước khi hiển thị trên app hoặc ghi prediction vào evaluation.

## Input

```json
{
  "article": {
    "article_id": "input_001",
    "title": "...",
    "text": "..."
  },
  "retrieved_contexts": [],
  "draft_output": {
    "document_label": "HAS_EVENT",
    "events": []
  }
}
```

## Output

```json
{
  "verified_output": {},
  "verification_report": {
    "schema_valid": true,
    "evidence_coverage": 0.95,
    "unsupported_fields": [],
    "repaired": false,
    "dropped_events": []
  }
}
```

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| Schema validation | Pydantic hoặc JSON Schema |
| Evidence check | string match, fuzzy match, optional semantic check |
| Self-verification | LLM 8B hoặc teacher LLM nếu cần |
| Repair | constrained repair prompt |
| Logging | JSONL + SQLite |

## Các lớp kiểm định

### 1. JSON validity check

Kiểm tra:

- output parse được JSON.
- không có markdown wrapper.
- không có text ngoài JSON.

Nếu lỗi, gọi repair prompt:

```text
Fix the following output into valid JSON only.
Do not add new information.
Do not remove evidence spans unless they are invalid JSON strings.
```

### 2. Schema compliance check

Kiểm tra:

- `document_label` thuộc `HAS_EVENT`, `NO_EVENT`.
- `event_type` thuộc taxonomy.
- `event_subtype` hợp lệ với `event_type`.
- `impact_sentiment` thuộc `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `MIXED`.
- `event_arguments` là object.
- `confidence` nằm trong `[0, 1]`.

### 3. Evidence span check

Mỗi event phải có `evidence_span`.

Check theo thứ tự:

1. Exact string nằm trong article text.
2. Nếu không exact, fuzzy match với đoạn gần nhất.
3. Nếu vẫn không có, kiểm tra trong retrieved contexts.
4. Nếu không tìm được evidence, đánh dấu unsupported.

Quy tắc:

- Field quan trọng không có evidence thì đưa về `null` hoặc loại.
- Event không có evidence thì drop hoặc chuyển thành warning.

### 4. Argument grounding check

Kiểm tra các argument có thật trong evidence hoặc article không.

Ví dụ với `CONTRACT`:

- `partner` phải xuất hiện trong bài hoặc context.
- `contract_value` phải có số tiền tương ứng.
- `project` phải có cụm dự án/gói thầu.

Ví dụ với `LEADERSHIP`:

- `person` phải xuất hiện.
- `role` phải xuất hiện.
- `action` như bổ nhiệm/miễn nhiệm/từ nhiệm phải xuất hiện.

Nếu argument không có căn cứ:

```json
{
  "field": "event_arguments.contract_value",
  "status": "UNSUPPORTED",
  "action": "set_null"
}
```

### 5. Taxonomy consistency check

Kiểm tra event type/subtype và arguments có khớp nhau không.

Ví dụ:

- `LEGAL_RISK` nên có `legal_authority`, `violation`, `penalty_value` nếu bài có.
- `CAPITAL` nên có `capital_before`, `capital_after`, `share_volume`, `issue_price` nếu bài có.
- `LEADERSHIP` nên có `person`, `role`, `action`.
- `CONTRACT` nên có `partner`, `contract_value`, `project` hoặc `product`.

Nếu subtype không phù hợp với event type, sửa về `null` hoặc subtype gần nhất nếu rule chắc chắn.

### 6. Contradiction check

Kiểm tra mâu thuẫn cơ bản:

- `document_label=NO_EVENT` nhưng `events` không rỗng.
- `document_label=HAS_EVENT` nhưng `events=[]`.
- `impact_sentiment=POSITIVE` cho sự kiện bị phạt/kiện tụng mà không có giải thích.
- ticker không khớp company name trong dictionary.

### 7. Self-verification prompt

Sau rule validation, có thể gọi LLM tự kiểm định.

Prompt:

```text
You are verifying an information extraction result.
Use only the article and retrieved evidence.
For each event field, decide whether it is SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.
Return JSON only.
Do not introduce new facts.
```

Output:

```json
{
  "event_id": "input_001_e01",
  "field_checks": [
    {
      "field": "event_type",
      "value": "CONTRACT",
      "support": "SUPPORTED",
      "evidence": "HPG trúng thầu..."
    }
  ],
  "overall_groundedness": 0.91,
  "recommended_action": "ACCEPT"
}
```

### 8. Repair policy

| Lỗi | Hành động |
| --- | --- |
| JSON parse fail | Repair format |
| Enum sai chính tả | Map về enum hợp lệ nếu rõ |
| Evidence span thiếu | Yêu cầu chọn lại evidence |
| Field unsupported | Set `null` hoặc xóa field |
| Event unsupported | Drop event |
| Nhiều lỗi nghiêm trọng | Trả `NO_EVENT` hoặc `UNCERTAIN` warning |

Không dùng repair để thêm thông tin mới.

## Hallucination metrics

| Metric | Công thức/Ý nghĩa |
| --- | --- |
| Evidence coverage | Số field có evidence / số field cần evidence |
| Unsupported field rate | Số field unsupported / tổng field |
| Unsupported event rate | Số event bị drop / tổng event draft |
| Schema validity rate | Output đúng schema sau repair |
| Repair success rate | Lỗi được sửa / lỗi phát hiện |
| Groundedness score | Điểm trung bình từ self-verification |

## Acceptance Criteria

- Không có event cuối cùng thiếu `evidence_span`.
- Không có field ngoài schema.
- Final output chỉ dùng `impact_sentiment` để biểu diễn chiều hướng tác động.
- Unsupported argument bị loại hoặc set `null`.
- Verification report được lưu cho từng run.

## Artifact

```text
runs/
  extraction/
    run_001_raw_output.json
    run_001_verified_output.json
    run_001_verification_report.json
```
