# M06: Workflow Extraction Online

M06 chạy student extraction trên clean articles bằng retrieval contexts do M04 tạo.

## Vai Trò

M06 là bước extraction online. Đến thời điểm M06 chạy, hệ thống giả định các bước
offline/online upstream đã chuẩn bị xong:

- M01 có clean articles.
- M02 có gold labels cho evaluation và pattern building.
- M03 có chunks, embeddings, BM25 và pattern refs gắn vào chunks.
- M04 có retrieval contexts chính thức cho từng article/config.

M06 không còn làm retrieval. Điều này quan trọng vì extraction quality và retrieval
quality cần được đo riêng. Nếu M06 tự retrieve, metric M04 có thể không phản ánh đúng
context thật sự đi vào prompt.

## Contract Hiện Tại

Input:

- `data/processed/articles_clean.jsonl`
- `data/retrieval/online_contexts.jsonl`

Output:

- `data/extraction/student_predictions.jsonl`
- `runs/extraction/<run_id>/prompt.txt`
- `runs/extraction/<run_id>/draft_output.json`
- `runs/extraction/<run_id>/verified_output.json`
- `runs/extraction/<run_id>/verification_report.json`
- `runs/extraction/<run_id>/result.json`

## Trình Tự Node

1. `preprocess`: normalize article đầu vào và refresh dictionary/taxonomy hints.
2. `load_retrieval_contexts`: tìm M04 retrieval run khớp article và `retrieval_config`.
3. `extraction`: build prompt và gọi student model, hoặc deterministic baseline khi chạy smoke local.
4. `validation_repair`: parse JSON, repair system identifiers, validate schema/taxonomy/grounding.
5. `verification`: loại unsupported events/arguments khi M07 được chọn.
6. `logging`: lưu prompt, draft, verified output, verification report và trace.

M06 không build retrieval queries, không retrieve chunks và không chọn patterns. Các
trách nhiệm đó nằm upstream:

- M03 gắn gold-derived `pattern_refs` vào chunks.
- M04 retrieve chunks và mang `pattern_refs` trong từng context.
- M06 đưa matched patterns vào prompt dưới từng retrieved context.

## Cách Load M04 Context

M06 đọc `retrieval_results_path`, mặc định:

```text
data/retrieval/online_contexts.jsonl
```

Với mỗi article, M06 tìm record:

```text
record.article_id == article.article_id
record.retrieval_config == config.retrieval_config
```

Nếu không có record đúng `retrieval_config`, M06 fallback sang record đầu tiên cùng
`article_id`. Fallback này giúp local smoke run không crash khi file retrieval chỉ có
một config, nhưng production nên giữ M04 và M06 cùng `retrieval_config`.

Ở M06, `retrieval_config` không phải là lệnh chạy retrieval mới. Nó chỉ là khóa để
chọn context record M04 đã được tạo trước đó. Các quyết định combine BM25/dense,
metadata, rule/LLM rerank hoặc coverage/MMR đều đã xảy ra ở M04.

Nếu M04 bật `llm_rerank_mode=student_env`, context record mà M06 đọc đã được student
model rerank listwise trước đó. M06 không gọi lại reranker và không tự đổi thứ tự
contexts ngoài việc cắt theo `max_contexts`.

Sau khi chọn record, M06 lấy tối đa `max_contexts` context đầu tiên. Pattern refs được
dedup từ `context.metadata.pattern_refs` để đưa vào debug trace và prompt.

## Config Quan Trọng

| Config | Ý nghĩa |
| --- | --- |
| `retrieval_results_path` | JSONL artifact do M04 ghi, mặc định `data/retrieval/online_contexts.jsonl` |
| `retrieval_config` | Chọn M04 retrieval record khớp khi có nhiều config |
| `max_contexts` | Giới hạn số M04 contexts đưa vào prompt |
| `student_provider` | `deterministic` cho local/test hoặc `env` cho student LLM cấu hình trong môi trường |
| `use_retrieval` | Debug switch; nếu false thì M06 chạy không có M04 contexts |
| `sync_postgres` | Lưu extraction run metadata, outputs, traces, `retrieval_run_id` và `context_chunk_ids` |

## Source Filtering

M06 có `sources` để lọc clean articles trước khi chạy batch extraction. Đây không phải
source crawl như M01. Nó chỉ lọc `data/processed/articles_clean.jsonl`.

Khi chạy từ admin graph có `run_id`, registry ghi file tạm:

```text
runs/admin/{run_id}/inputs/articles_filtered.jsonl
```

Mục đích là giữ file gốc không đổi. Nếu admin chọn `sources=["cafef"]`, M06 chỉ chạy
trên clean articles có `record["source"] == "cafef"`.

## Prompting

Prompt dùng grounded prompting và self-verification instructions:

- chỉ output JSON;
- có `label_reason` cho document label;
- có `event_reason` cho từng event;
- giữ private reasoning ở bên trong, chỉ expose concise reasons;
- mỗi event cần `evidence_span` grounded trong article;
- retrieved contexts có compact metadata và `matched_patterns`.

Prompt gồm các phần chính:

| Phần | Nội dung |
| --- | --- |
| `output_schema` | Shape JSON cần trả |
| `taxonomy` | Event types/subtypes liên quan |
| `grounding_rules` | Quy tắc evidence, reason, sentiment, no-event |
| `reasoning_policy` | Yêu cầu reasoning riêng tư, chỉ xuất reason ngắn |
| `retrieved_contexts` | Context text, score, metadata, matched patterns |
| `input_article` | Article cần extract |

M06 không yêu cầu model in chain-of-thought. `label_reason` và `event_reason` là
summary ngắn, grounded theo evidence. Đây là khác biệt quan trọng: reason là output
audit được phép lưu, không phải hidden reasoning.

## Output Schema

Student output hợp lệ cần có:

```json
{
  "article_id": "article_001",
  "document_label": "HAS_EVENT",
  "label_reason": "Bài viết có sự kiện doanh nghiệp cụ thể được nêu trực tiếp.",
  "events": [
    {
      "event_id": "article_001_e01",
      "ticker": "HPG",
      "company_name": "Hoa Phat",
      "event_type": "CONTRACT",
      "event_subtype": "BIDDING_WIN",
      "event_summary": "...",
      "event_reason": "...",
      "event_arguments": {},
      "impact_sentiment": "POSITIVE",
      "evidence_span": "...",
      "source_url": "...",
      "published_at": "...",
      "confidence": 0.9
    }
  ],
  "warnings": [],
  "model_info": {}
}
```

Nếu `document_label=NO_EVENT`, `events` phải rỗng và vẫn cần `label_reason`.

## Giới Hạn Text

M06 có chủ ý trim prompt inputs để student call không vượt context:

| Config | Mặc định | Áp dụng cho |
| --- | ---: | --- |
| `max_article_chars` | `0` | Main input article text; `0` nghĩa là không cắt |
| `max_context_chars` | `0` | Text của mỗi retrieved context; `0` nghĩa là không cắt |
| `max_pattern_output_chars` | `0` | Gold pattern output view gắn với context; `0` nghĩa là không cắt |
| `max_prompt_chars` | `0` | Final rendered extraction prompt; `0` nghĩa là không áp prompt budget |

Nếu rendered prompt quá dài, M06 thử lại theo thứ tự:

1. toàn bộ selected contexts với giới hạn bình thường;
2. top 3 contexts với article/context/pattern limits ngắn hơn;
3. top 1 context với limits ngắn hơn;
4. không có retrieval contexts, article limit cũng ngắn hơn.

Verification có cap riêng: article text được trim ở 4000 ký tự và mỗi retrieved
context được trim ở 1200 ký tự trong verification prompt.

## Validation Repair

Sau khi student trả raw text, M06 chạy validation/repair:

1. Parse JSON.
2. Gắn lại `article_id` nếu model thiếu hoặc trả sai.
3. Chuẩn hóa `document_label`.
4. Đảm bảo `label_reason` tồn tại.
5. Đảm bảo mỗi event có `event_reason`.
6. Validate event type/subtype theo taxonomy.
7. Validate grounding của `evidence_span`.
8. Nếu output không thể repair, tạo fallback `UNCERTAIN` hoặc `NO_EVENT` tùy lỗi.

Repair không được thêm fact mới. Nó chỉ sửa cấu trúc, field thiếu an toàn, hoặc loại
bỏ phần không hợp lệ.

## Verification Khi Chọn M07

M07 là modifier của M06. Khi M07 được chọn, M06 không thêm `--disable-verification`,
và workflow chạy bước verification sau validation repair.

Verification kiểm tra:

- event có evidence trong article không;
- event argument có được support bởi text không;
- field như contract value, project, partner có bị bịa không;
- event không có evidence có nên bị drop không;
- nếu drop hết events thì document label có cần chuyển thành `NO_EVENT` không.

Verification output gồm:

```text
runs/extraction/<run_id>/verification_report.json
runs/extraction/<run_id>/verified_output.json
```

Mục tiêu của verification là giảm hallucination, không phải làm retrieval hoặc suy ra
fact mới.

## PostgreSQL Sync

Khi `sync_postgres=true`, M06 lưu:

| Bảng | Nội dung |
| --- | --- |
| `extraction_runs` | Metadata run, config, output, `retrieval_run_id`, `context_chunk_ids` |
| `extraction_node_traces` | Trace từng node như preprocess, extraction, validation, verification |

`retrieval_run_id` và `context_chunk_ids` là cầu nối từ extraction result về M04
contexts. Nếu một event sai, có thể kiểm tra context nào đã đi vào prompt và score
breakdown của context đó ở M04.

## Failure Cases

| Trường hợp | Hành vi |
| --- | --- |
| Không tìm thấy retrieval record | M06 có thể chạy không context nếu `use_retrieval=false`; nếu vẫn bật retrieval thì log warning rõ |
| Context rỗng | Prompt vẫn build được nhưng `retrieved_contexts=[]` |
| Prompt quá dài | Dùng fallback giảm context/giảm text như bảng giới hạn |
| Student output không parse được JSON | Validation repair tạo fallback có warning |
| Event thiếu evidence | Bị validation/verification hạ confidence hoặc loại |
| Verification drop hết events | Document label chuyển về `NO_EVENT` để tránh mâu thuẫn |

## Debug Artifacts

Mỗi article run có thư mục:

```text
runs/extraction/<run_id>/
  prompt.txt
  draft_output.json
  verified_output.json
  verification_report.json
  result.json
```

Khi debug extraction, nên đọc theo thứ tự:

1. `prompt.txt`: context và instruction có đủ không.
2. `draft_output.json`: student model sinh gì.
3. `verification_report.json`: field/event nào bị xem là unsupported.
4. `verified_output.json`: output cuối sau verification.
5. `result.json`: trace tổng hợp để nối với DB/API.
