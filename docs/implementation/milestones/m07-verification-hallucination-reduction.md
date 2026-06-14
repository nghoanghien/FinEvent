# M7: Verification and Hallucination Reduction

## Mục tiêu

Kiểm tra output của LLM trước khi chấp nhận làm kết quả cuối. Milestone này giúp project không chỉ “gọi LLM”, mà có cơ chế grounded extraction dựa trên evidence.

## Input

```text
draft extraction output
article text
retrieved contexts
schema/taxonomy
```

## Output

```text
verified output
verification report
hallucination metrics
```

## Công nghệ

- Pydantic/JSON Schema.
- Fuzzy string matching.
- Rule-based validator.
- Self-verification prompt.
- JSON repair prompt.

## Cách triển khai chi tiết

### Bước 1: JSON validity

Kiểm tra output parse được JSON. Nếu không:

- extract JSON block nếu có.
- gọi repair prompt.
- nếu vẫn fail, trả validation error.

### Bước 2: Schema compliance

Kiểm tra:

- document label.
- event type.
- event subtype hợp lệ.
- impact sentiment.
- confidence.
- event arguments là object.

### Bước 3: Evidence span check

Mỗi event phải có evidence span.

Check theo thứ tự:

1. exact match trong article.
2. fuzzy match trong article.
3. exact/fuzzy match trong retrieved contexts.
4. nếu không có, event unsupported.

### Bước 4: Argument grounding

Mỗi argument quan trọng phải có dấu vết trong evidence/article.

Ví dụ:

- `contract_value` phải có số tiền.
- `person` phải có tên người.
- `legal_authority` phải có cơ quan.
- `project` phải có tên dự án/gói thầu.

Field unsupported thì set `null` hoặc loại khỏi output.

### Bước 5: Taxonomy consistency

Kiểm tra event type/subtype và arguments có khớp nhau không.

Ví dụ:

- `LEADERSHIP` nhưng không có person/role/action thì cảnh báo.
- `CONTRACT` nhưng không có partner/project/product/value nào thì hạ confidence.
- `LEGAL_RISK` mà impact sentiment positive thì yêu cầu evidence giải thích, nếu không hạ confidence/cảnh báo.

### Bước 6: Self-verification

LLM verifier đọc article + output và trả:

- field support status.
- evidence.
- groundedness score.
- recommended action.

Verifier không được thêm thông tin mới.

### Bước 7: Repair/drop policy

| Lỗi | Hành động |
| --- | --- |
| JSON lỗi | Repair format |
| Enum sai | Map nếu chắc chắn, nếu không reject |
| Evidence thiếu | Yêu cầu chọn lại evidence |
| Argument unsupported | Set null hoặc xóa |
| Event unsupported | Drop event |
| Mâu thuẫn nghiêm trọng | Trả warning hoặc `NO_EVENT` |

## Kiểm thử

- Test event không evidence bị drop.
- Test argument unsupported bị set null.
- Test enum sai bị reject/map.
- Test final output không có field ngoài schema.

## Metrics

- evidence coverage.
- unsupported field rate.
- unsupported event rate.
- post-verification hallucination rate.
- repair success rate.
- groundedness score.

## Done Criteria

- Không có final event thiếu evidence.
- Verification report được lưu cho mọi run.
- Hallucination metrics có trong evaluation.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Fuzzy match quá dễ | Đặt threshold và log match score |
| Verifier cũng hallucinate | Bắt verifier trả evidence và không thêm fact |
| Verification làm mất recall | Báo cáo trade-off recall vs hallucination |

