# Multi-Event-Aware Retrieval And Pattern Selection

## Mục tiêu

`multi_event_aware_hybrid` là strategy bổ sung cho các bài báo có nhiều event type.
Strategy này không thay thế mặc định cũ, mà dùng khi cần giảm rủi ro context và
few-shot pattern bị một event áp đảo.

## Cách hoạt động

1. Query legacy vẫn được tạo theo title, ticker/event, company/event và event type.
2. Nếu config dùng `query_mode="event_intent"`, hệ thống tạo thêm query riêng cho
   từng event type trong `event_type_hints`.
3. Chunk retrieval Stage 1 vẫn lấy candidate từ bể chung gồm document/section/paragraph.
4. Chunk final selection dùng `coverage_mmr`:
   - ưu tiên candidate có relevance cao;
   - cộng điểm cho event type/query intent chưa được cover;
   - trừ điểm cho chunk trùng lặp nhiều với context đã chọn;
   - hạn chế một event type chiếm quá nhiều context cuối.
5. Pattern selection cũng dùng cùng `query_mode="event_intent"`:
   - tạo pattern query tổng hợp legacy;
   - tạo thêm pattern query riêng cho từng event type detected;
   - chọn pattern theo `coverage` trước, rồi fill slot còn lại bằng score.

Hệ thống không query toàn bộ taxonomy. Cả chunk và pattern chỉ tách intent theo
những event type có trong `event_type_hints` của bài đầu vào.

## Config

Config mới nằm trong `DEFAULT_RETRIEVAL_CONFIGS`:

```text
multi_event_aware_hybrid
top_k_stage1 = 75
top_k_final = 10
query_mode = event_intent
selection_strategy = coverage_mmr
adaptive_top_k_final = true
```

Adaptive context budget:

| Số event type trong query | Context tối đa |
| ---: | ---: |
| 0-1 | 5 |
| 2 | 8 |
| >=3 | 10 |

Trong online extraction, `max_contexts` vẫn là lớp cắt cuối. Khi dùng strategy này
trên Admin UI nên đặt `max_contexts` khoảng `8-10`.

`pattern_count` vẫn là giới hạn cuối cho số few-shot pattern. Nếu bài có nhiều event
type hơn `pattern_count`, pattern selector sẽ cover được tối đa `pattern_count` event
type bằng pattern, sau đó mới fill thêm theo score khi còn slot.

## Metrics mới

Retrieval evaluation có thêm các metric:

| Metric | Ý nghĩa |
| --- | --- |
| `event_type_coverage_at_5/10` | Tỷ lệ gold event type được cover trong top K context |
| `event_evidence_coverage_at_5/10` | Tỷ lệ gold event có evidence chunk nằm trong top K |
| `unique_event_types_at_5/10` | Số event type khác nhau trong top K |
| `dominance_ratio_at_5/10` | Tỷ lệ event type chiếm nhiều nhất trong top K |

## Khi nào dùng

Dùng `multi_event_aware_hybrid` khi bài báo hoặc batch có dấu hiệu chứa nhiều
corporate actions, ví dụ M&A đi kèm chia cổ tức, thay đổi lãnh đạo hoặc tăng vốn.
Với bài báo một event chính, `metadata_aware_hybrid` vẫn là lựa chọn gọn và ít nhiễu hơn.
