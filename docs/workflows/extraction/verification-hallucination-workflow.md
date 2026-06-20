# Verification và Hallucination Reduction Workflow

## Mục tiêu

Workflow này kiểm tra output của LLM trước khi chấp nhận làm kết quả cuối. Nó
giảm hallucination bằng cách yêu cầu mỗi event và argument quan trọng phải có
bằng chứng trong bài báo hoặc context truy hồi.

Workflow chạy sau extraction và schema validation:

```text
draft output -> verification -> verified output
```

## Input

```json
{
  "article": {
    "article_id": "input_001",
    "title": "...",
    "text": "..."
  },
  "retrieved_contexts": [
    {
      "chunk_id": "ctx_001",
      "title": "...",
      "text": "..."
    }
  ],
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
    "schema_valid_before_verification": true,
    "schema_valid_after_verification": true,
    "event_checks": [],
    "field_checks": [],
    "unsupported_fields": [],
    "dropped_events": [],
    "repairs": [],
    "metrics": {}
  }
}
```

## Công nghệ

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Schema check | Validator nội bộ trong `finevent.schema.validation` | Kiểm tra enum, subtype, field bắt buộc |
| Evidence check | Exact match + fuzzy match bằng `SequenceMatcher` | Tìm bằng chứng cho `evidence_span` |
| Argument grounding | Rule-based field check | Kiểm tra value của argument có căn cứ không |
| Taxonomy check | `event_taxonomy_v1.json` | Kiểm tra event type, subtype, nhóm argument cốt lõi |
| Repair/drop policy | Rule-based policy | Drop event unsupported, set-null argument unsupported |
| Optional self-verification | Prompt builder cho LLM verifier | Dùng trong thí nghiệm nâng cao, không thêm fact mới |
| Logging | JSON files + PostgreSQL JSONB | Lưu report và metric cho debug/evaluation |

## Quy trình chi tiết

### 1. Nhận draft output

Draft output là kết quả sau bước `validation_repair`. Ở thời điểm này JSON đã
parse được và có các field cơ bản, nhưng nội dung có thể vẫn hallucinate.

### 2. Strip field ngoài schema

Verifier bỏ các field không nằm trong event schema. Ví dụ:

```json
{
  "impact_severity": "HIGH"
}
```

Field này bị drop vì project chỉ dùng `impact_sentiment` để biểu diễn chiều
hướng tác động.

### 3. Evidence span check

Mỗi event được kiểm tra evidence:

1. exact match trong article;
2. fuzzy match trong article;
3. exact/fuzzy match trong retrieved contexts;
4. không có match thì đánh dấu unsupported.

Policy mặc định:

| Trạng thái evidence | Hành động |
| --- | --- |
| `SUPPORTED` | Giữ event |
| `PARTIALLY_SUPPORTED` | Giữ event, ghi score |
| `UNSUPPORTED` | Drop event |

### 4. Argument grounding check

Verifier duyệt từng key trong `event_arguments`. Nếu value không xuất hiện hoặc
không gần khớp với evidence/article/context thì không giữ nguyên value đó.

Ví dụ:

```json
{
  "event_arguments": {
    "project": "gói thầu xây dựng nhà máy",
    "contract_value": "500 tỷ đồng"
  }
}
```

Nếu bài báo có `project` nhưng không có `500 tỷ đồng`, output sau verification:

```json
{
  "event_arguments": {
    "project": "gói thầu xây dựng nhà máy",
    "contract_value": null
  }
}
```

### 5. Taxonomy consistency check

Verifier kiểm tra các nhóm argument cốt lõi:

| Event type | Ít nhất nên có một trong các field |
| --- | --- |
| `CONTRACT` | `partner`, `project`, `product`, `package_name`, `contract_value` |
| `CAPITAL` | `share_volume`, `issue_price`, `capital_before`, `capital_after`, `bond_value` |
| `LEADERSHIP` | `person`, `role`, `action` |
| `LEGAL_RISK` | `legal_authority`, `violation`, `case_name`, `penalty_value` |
| `EXPANSION` | `project`, `location`, `investment_value`, `capacity`, `market` |

Nếu thiếu nhóm argument cốt lõi, event không nhất thiết bị drop ngay, nhưng
confidence bị hạ và report có warning để phục vụ error analysis.

### 6. Contradiction check

Các mâu thuẫn cơ bản:

- `HAS_EVENT` nhưng tất cả event bị drop;
- subtype không thuộc event type;
- `LEGAL_RISK` nhưng `impact_sentiment=POSITIVE`;
- field ngoài schema vẫn xuất hiện trong output.

Policy:

| Lỗi | Hành động |
| --- | --- |
| Subtype sai | Set `event_subtype=null` |
| Field ngoài schema | Drop field |
| Event không evidence | Drop event |
| Argument không grounded | Set `null` |
| Không còn event | Đổi `document_label=NO_EVENT` |

### 7. Optional self-verification prompt

M07 có sẵn prompt builder:

```python
build_self_verification_prompt(...)
```

Prompt yêu cầu LLM verifier:

- chỉ dùng article và retrieved contexts;
- không thêm fact mới;
- kiểm tra từng field;
- trả JSON only;
- gợi ý `set_null`, `drop_field` hoặc `drop_event`.

Đây là hook cho thí nghiệm nâng cao ở M08/M09, không phải dependency bắt buộc
trong baseline.

### 8. Metrics

Workflow sinh metric:

| Metric | Công thức/ý nghĩa |
| --- | --- |
| `evidence_coverage` | event có evidence support / event cần kiểm tra |
| `unsupported_field_rate` | field unsupported / tổng field được kiểm tra |
| `unsupported_event_rate` | event bị drop / event draft |
| `verified_event_retention_rate` | event verified / event draft |
| `schema_repair_count` | số thao tác repair/drop/set-null |
| `groundedness_score` | điểm tổng hợp mức độ grounded của field checks |

## Artifact

```text
runs/extraction/<run_id>/
  draft_output.json
  verified_output.json
  verification_report.json
  result.json
  trace.jsonl
```

## Acceptance Criteria

- Không có final event thiếu `evidence_span`.
- Unsupported argument bị set `null` hoặc drop theo policy.
- Final output không có field ngoài schema.
- Public result có `verification_report` và `hallucination_metrics`.
- Workflow trace có node `verification`.
- Hallucination metrics đủ để M08 tính pre/post verification và ablation.
