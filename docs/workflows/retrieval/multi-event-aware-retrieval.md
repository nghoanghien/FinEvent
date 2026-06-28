# Retrieval Có Nhận Biết Nhiều Event

`multi_event_aware_hybrid` là retrieval strategy cho bài viết có thể chứa nhiều
corporate event type.

## Cách Hoạt Động

1. Legacy queries vẫn được build từ title, ticker/event keywords, company/event keywords và event type hints.
2. Với `query_mode="event_intent"`, retrieval build thêm một query cho mỗi event type trong `event_type_hints`.
3. Stage 1 retrieve candidates từ shared chunk index: document, section và paragraph chunks.
4. Strategy selection dùng `coverage_mmr` trên pool rộng hơn `max_contexts`:
   - ưu tiên relevance cao;
   - thưởng event/query intents chưa được cover;
   - phạt near-duplicate context;
   - giới hạn việc một event type áp đảo context pool.
5. Nếu M04 bật `llm_rerank_mode`, student LLM rerank listwise sau coverage/MMR. Đây là bước xếp hạng cuối cùng.
6. M04 cắt theo `max_contexts` rồi ghi context pack cho M06.
7. Pattern refs không được retrieve riêng. M03 gắn `pattern_refs` vào chunks, và M04 mang các refs đó trong từng retrieved context.

## Config

`multi_event_aware_hybrid` hiện dùng:

```text
top_k_stage1 = 75
top_k_final = 10
query_mode = event_intent
selection_strategy = coverage_mmr
adaptive_top_k_final = true
```

Ngân sách context thích ứng:

| Số event type | Final context budget |
| ---: | ---: |
| 0-1 | 5 |
| 2 | 8 |
| >=3 | 10 |

Trong admin UI, M04 và M06 vẫn áp dụng `max_contexts` làm cap cuối. Với multi-event
run nên dùng `8-10`.

Không có config `pattern_count`. Prompt patterns đến từ `pattern_refs` gắn trên
retrieved chunks.

## Khi Nào Dùng

Nên dùng `multi_event_aware_hybrid` khi bài đầu vào có dấu hiệu chứa nhiều event type,
ví dụ:

- vừa có tin hợp đồng vừa có mở rộng dự án;
- vừa có thay đổi lãnh đạo vừa có phát hành cổ phiếu;
- bài tổng hợp nhiều doanh nghiệp/mã cổ phiếu;
- `event_type_hints` có từ 2 event type trở lên.

Với bài single-event rõ ràng, `metadata_aware_hybrid` thường đủ và rẻ hơn.

## Coverage/MMR

Selection không chỉ sort theo score. Nó cân bằng:

```text
final_score = relevance_score
            + coverage_bonus_for_uncovered_event_intent
            - duplicate_penalty
            - dominance_penalty
```

Ý nghĩa:

- `relevance_score`: chunk vẫn phải liên quan.
- `coverage_bonus`: event type chưa có context sẽ được ưu tiên.
- `duplicate_penalty`: tránh nhiều chunk gần như giống nhau.
- `dominance_penalty`: tránh một event type chiếm hết context budget.

Điểm này giúp M06 có đủ evidence cho nhiều event, thay vì chỉ thấy event nổi bật nhất
và bỏ sót event phụ.

## Quan Hệ Với M06

M04 quyết định context pack. Với `multi_event_aware_hybrid`, coverage/MMR chạy trước
để bảo vệ context cho event phụ và tạo một candidate pool rộng hơn context cuối cùng.
Nếu `llm_rerank_mode` bật, listwise LLM rerank chạy sau đó như bước lọc/xếp hạng cuối
cùng trước khi M04 cắt theo `max_contexts`.

M06 không blend nhiều artifact output từ nhiều recipe và không tự gọi lại retrieval. Nếu admin đặt
`retrieval_config=multi_event_aware_hybrid` ở M06, M06 chỉ tìm record M04 có cùng
config đó trong `online_contexts.jsonl`; recipe này phải được M04 chạy trước.

Vì vậy khi muốn đánh giá multi-event, cần chạy M04 bằng
`multi_event_aware_hybrid` trước, rồi M06 dùng cùng `retrieval_config`.

## Metrics

Retrieval evaluation gồm:

| Metric | Ý nghĩa |
| --- | --- |
| `event_type_coverage_at_5/10` | Tỷ lệ gold event types được cover trong top K contexts |
| `event_evidence_coverage_at_5/10` | Tỷ lệ gold events có evidence chunk trong top K |
| `unique_event_types_at_5/10` | Số event type xuất hiện trong top K |
| `dominance_ratio_at_5/10` | Tỷ lệ event type áp đảo nhất trong top K |

## Failure Cases

| Trường hợp | Rủi ro | Cách xử lý |
| --- | --- | --- |
| `event_type_hints` thiếu event phụ | Không sinh query intent cho event đó | Cải thiện M01/M02 hinting hoặc rely vào title/body query |
| Một event có quá ít candidate | Coverage bonus không có gì để chọn | Giữ top relevance chung, log miss trong metrics |
| Context quá nhiều duplicate | M06 prompt phí context budget | Tăng duplicate penalty hoặc giảm `max_contexts` |
| `max_contexts` quá thấp | Không đủ context cho nhiều event | Dùng 8-10 cho multi-event |
| Pattern refs thiếu | Prompt thiếu ví dụ schema | Kiểm tra M03 chunk-pattern mapping |
