# M04: Retrieval Online Và Reranking

M04 tạo retrieval contexts cho online extraction. Nó dùng artifacts offline từ M03 và
ghi context records sẵn sàng cho M06. M04 không còn chỉ là bước so sánh strategy
riêng lẻ; nhiệm vụ chính trong graph là tạo context pack chính thức cho M06. Luồng
so sánh nhiều retrieval recipe vẫn còn qua command `finevent.retrieval compare`, còn
M06 không còn tự retrieve chunk nữa.

## Vai Trò Trong Project

M03 là bước chuẩn bị offline: chunks, embeddings, BM25 index và `pattern_refs` gắn
trên chunk.

M04 là lớp online retrieval:

1. Load clean articles.
2. Build retrieval queries riêng cho từng article.
3. Retrieve candidate chunks từ BM25/dense/hybrid signals.
4. Rerank và chọn final context pack.
5. Mang `pattern_refs` của từng chunk vào context metadata.
6. Ghi retrieval contexts, logs và metrics.

M06 đọc output của M04 và tập trung vào extraction/verification. Cách tách này giúp
retrieval và extraction có thể test riêng.

## Vì Sao M04 Được Gộp Thành Online Retrieval

Trước đây retrieval xuất hiện ở hai nơi: M04 đánh giá strategy, còn M06 lại có logic
retrieve riêng trong extraction workflow. Cách đó gây ra ba vấn đề:

- metric ở M04 không chắc phản ánh đúng context mà M06 thật sự dùng;
- khó debug vì retrieval logs và extraction traces có thể lệch nhau;
- pattern selection dễ bị tách khỏi chunk evidence.

Thiết kế hiện tại đưa retrieval runtime về M04. M04 sinh context pack chính thức,
M06 chỉ tiêu thụ context pack đó. Nhờ vậy:

- retrieval quality được đo đúng trên artifact sẽ đi vào extraction;
- M06 prompt trace có thể truy ngược `retrieval_run_id` và `context_chunk_ids`;
- `multi_event_aware_hybrid` được đánh giá ở retrieval stage, không bị trộn mơ hồ
  trong extraction stage.

## Input

```text
data/processed/articles_clean.jsonl
data/processed/chunks.jsonl
data/retrieval/bm25_index.pkl
data/retrieval/chunk_embeddings.jsonl
data/labels/events_gold.jsonl
```

`events_gold.jsonl` là optional cho runtime retrieval nhưng cần cho retrieval metrics.
Khi có gold labels, M04 đánh giá retrieved chunks có cover gold evidence hay không.

## Output

```text
data/retrieval/online_contexts.jsonl
data/retrieval/online_retrieval_logs.jsonl
reports/evaluation/online_retrieval_metrics.csv
reports/evaluation/online_retrieval_error_analysis.md
```

Nếu bật PostgreSQL sync, M04 còn ghi:

- `retrieval_runs`
- `retrieval_run_contexts`

## Luồng Xử Lý Chi Tiết

Một run M04 batch đi qua các bước:

1. Load articles từ `articles_path`.
2. Apply `limit`/`offset` nếu có.
3. Load chunks, BM25 index và embeddings từ M03.
4. Với mỗi article, build query bundle.
5. Retrieve candidate chunks theo `retrieval_config`.
6. Chạy strategy selection/coverage để lấy pool rộng hơn cho LLM.
7. Nếu `llm_rerank_mode` bật, rerank listwise pool đó bằng student LLM.
8. Ghi một record vào `online_contexts.jsonl`.
9. Ghi log chi tiết vào `online_retrieval_logs.jsonl`.
10. Nếu có gold labels, build eval cases và ghi metrics/error analysis.
11. Nếu bật sync, ghi `retrieval_runs` và `retrieval_run_contexts` vào PostgreSQL.

M04 không sửa `articles_clean.jsonl` và không ghi predictions. M04 có thể gọi student
LLM khi `llm_rerank_mode=student_env`; lời gọi này chỉ dùng để rerank retrieval
contexts, không sinh event extraction.

## Contract Của Context Record

Mỗi output record là retrieval result cho một cặp article/config:

```json
{
  "retrieval_run_id": "retrieval_article_001_metadata_aware_hybrid",
  "article_id": "article_001",
  "retrieval_config": "metadata_aware_hybrid",
  "query_count": 4,
  "contexts": [
    {
      "rank": 1,
      "chunk_id": "article_001_p02",
      "article_id": "article_001",
      "score": 0.91,
      "text": "Evidence-bearing chunk text...",
      "score_breakdown": {
        "dense_score": 0.82,
        "bm25_score": 0.76,
        "metadata_score": 1.0,
        "rule_score": 0.2
      },
      "metadata": {
        "chunk_level": "paragraph",
        "tickers": ["HPG"],
        "event_type_hints": ["CONTRACT"],
        "pattern_refs": []
      }
    }
  ],
  "matched_patterns": []
}
```

`matched_patterns` được suy ra từ retrieved contexts. M04 không query một pattern
vector index riêng.

Các field quan trọng:

| Field | Ý nghĩa |
| --- | --- |
| `retrieval_run_id` | ID ổn định để M06 và DB trace tham chiếu |
| `article_id` | Article đầu vào của retrieval run |
| `retrieval_config` | Recipe lấy candidate và tính điểm ban đầu |
| `contexts` | Danh sách context đã rerank, theo thứ tự rank |
| `score_breakdown` | Thành phần điểm giúp debug strategy |
| `metadata.pattern_refs` | Pattern records đã gắn với chunk từ M03 |
| `matched_patterns` | Danh sách pattern refs dedup từ context pack |
| `llm_rerank` | Tóm tắt listwise rerank nếu M04 bật LLM reranker |

## Retrieval Strategies

| Strategy | Mục đích |
| --- | --- |
| `bm25_only` | Lexical baseline cho trigger words và tên riêng |
| `dense_only` | Semantic baseline từ M03 chunk embeddings |
| `hybrid` | Kết hợp dense và BM25 |
| `metadata_aware_hybrid` | Hybrid cộng thêm ticker/company/event/source/recency metadata |
| `rule_aware_rerank` | Thêm rule về evidence và penalty cho generic market text |
| `llm_reasoning_rerank` | Recipe cũ có LLM relevance slot; production hiện dùng listwise rerank qua `llm_rerank_mode` |
| `multi_event_aware_hybrid` | Thêm event-intent queries và coverage/MMR cho bài nhiều event |

`retrieval_config` không có nghĩa là bỏ logic hybrid để chọn một phương pháp retrieve
đơn lẻ. Nó là tên của một recipe scoring/rerank:

- `bm25_only` và `dense_only` là baseline để đo từng signal riêng.
- `hybrid` kết hợp BM25 và dense embedding.
- `metadata_aware_hybrid` cộng thêm metadata/source/recency.
- `rule_aware_rerank` cộng thêm rule score deterministic.
- `llm_reasoning_rerank` giữ slot LLM relevance cho thí nghiệm/ablation.
- `multi_event_aware_hybrid` vẫn là hybrid, nhưng thêm event-intent queries và
  coverage/MMR để không bỏ sót event phụ trong cùng bài.

M04 `run-batch` phải chọn một `retrieval_config` vì M06 cần một context pack xác định
cho mỗi article/config. Nếu muốn đánh giá nhiều recipe cùng lúc, dùng
`python -m finevent.retrieval compare`; command này vẫn chạy các recipe mặc định và
ghi `retrieval_logs.jsonl`, `retrieval_metrics.csv`, error analysis. Kết quả compare
dùng để quyết định recipe production, còn M06 không trộn output của nhiều recipe trong
cùng một lần extraction.

## Score Breakdown

Mỗi candidate có điểm tổng hợp từ nhiều tín hiệu:

```text
score =
  dense_weight * dense_score
+ bm25_weight * bm25_score
+ metadata_weight * metadata_score
+ recency_weight * recency_score
+ rule_weight * rule_score
```

Không phải strategy nào cũng dùng đủ mọi thành phần. Ví dụ:

- `bm25_only` chỉ dùng BM25.
- `dense_only` chỉ dùng dense similarity.
- `metadata_aware_hybrid` dùng dense, BM25, metadata và recency/source.
- `rule_aware_rerank` thêm rule score deterministic.
- `llm_reasoning_rerank` thêm slot cho LLM relevance score trong ablation.

Sau score ban đầu và strategy selection, M04 production còn có thể chạy listwise LLM
rerank như bước xếp hạng cuối cùng. Khi đó `score_breakdown` có thêm `llm_rank`,
`llm_relevance_score`, `llm_relevance_label`, `llm_reasoning_summary`,
`llm_rerank_mode` và `llm_rerank_model`.

`score_breakdown` phải được giữ trong output để khi retrieval sai có thể biết sai do
embedding, keyword, metadata hay rule.

## Query Decomposition

M04 build nhiều query view từ article:

| Query type | Nguồn |
| --- | --- |
| `title` | Title bài viết |
| `ticker_event` | Ticker + event keywords + title |
| `company_event` | Company names + event keywords |
| `event_type` | Event type/subtype hints + event keywords |
| `body_fallback` | Đoạn mở đầu khi title/metadata yếu |

Với `multi_event_aware_hybrid`, M04 build thêm một event-intent query cho mỗi event
type phát hiện trong `event_type_hints`. Nó không query toàn bộ taxonomy enum.

Ví dụ một article có ticker HPG, event keyword "trúng thầu" và event hint
`CONTRACT` có thể sinh các query:

```json
[
  {
    "query_type": "title",
    "text": "HPG trúng thầu dự án cung cấp thép",
    "weight": 1.0
  },
  {
    "query_type": "ticker_event",
    "text": "HPG trúng thầu dự án cung cấp thép",
    "weight": 1.0
  },
  {
    "query_type": "event_type",
    "text": "CONTRACT trúng thầu hợp đồng dự án",
    "weight": 0.65
  }
]
```

Query decomposition là cách giảm rủi ro một query duy nhất bỏ sót evidence vì title
thiếu ticker, bài dùng tên công ty thay mã, hoặc event keyword nằm trong body.

## Reranking

Reranking kết hợp:

- dense similarity;
- BM25 lexical score;
- ticker/company/source/event metadata overlap;
- recency/source signal;
- deterministic rule score;
- optional listwise LLM rerank bằng student model ở bước cuối.

Với bài multi-event, strategy selection trước LLM dùng coverage/MMR:

- giữ chunk có score cao;
- thưởng event intent chưa được cover;
- giảm near-duplicate chunks;
- tránh một event type áp đảo pool đưa vào LLM hoặc context cuối khi LLM tắt.

### LLM Listwise Rerank

M04 `run-batch` mặc định dùng `llm_rerank_mode=student_env`, nghĩa là dùng chính
student model trong `.env` làm reranker. Đây là bước cuối của M04 ranking. Trước đó
M04 vẫn chạy strategy selection như bình thường; riêng `multi_event_aware_hybrid` vẫn
chạy coverage/MMR để giữ đa dạng event. Điểm khác là pool trước LLM được giữ rộng hơn,
tối thiểu bằng `llm_rerank_top_n`, rồi LLM mới lọc/xếp hạng lần cuối trước khi M04 cắt
xuống `max_contexts`.

Prompt không nhét nguyên toàn bộ bài báo gốc của từng chunk. Mỗi candidate chỉ mang:

- title/source/url/published_at của bài gốc;
- `article_summary_preview` từ document chunk;
- chunk text đã cắt bởi `llm_rerank_max_candidate_chars`;
- tickers/company/event hints, compact `pattern_refs` và `score_breakdown`.

Cách này cho LLM đủ ngữ cảnh về dòng sự kiện và thời điểm mà không làm prompt quá dài.
Output mong muốn:

```json
{
  "ranked_candidate_ids": [5, 2, 12, 1],
  "judgments": [
    {
      "candidate_id": 5,
      "chunk_id": "article_001_p02",
      "relevance_score": 0.92,
      "relevance_label": "HIGH",
      "evidence_span": "...",
      "reasoning_summary": "Ứng viên cùng công ty, cùng loại sự kiện và có evidence cụ thể."
    }
  ]
}
```

Parser cũng chấp nhận dạng array ngắn như `[5, 2, 12, 1]`. Không yêu cầu model expose
chain-of-thought; chỉ lưu `reasoning_summary` ngắn để audit vì sao candidate được đẩy
lên hoặc hạ xuống.

### Multi-Event Selection

Với bài nhiều event, context pack không nên bị một event type áp đảo. Strategy
`multi_event_aware_hybrid` dùng event intent và coverage/MMR để ưu tiên:

- ít nhất một context cho mỗi event type quan trọng nếu có candidate đủ điểm;
- đa dạng paragraph/section để tránh duplicate;
- evidence-bearing chunk thay vì document-level chunk quá chung chung;
- giới hạn pool theo adaptive budget mở rộng; nếu LLM tắt thì đây cũng là context cuối,
  nếu LLM bật thì LLM rerank pool đó trước khi M04 cắt theo `max_contexts`.

## Metrics

M04 đánh giá retrieval quality bằng gold labels khi có.

Gold relevance được build bằng cách match từng `evidence_span` vào chunks cùng
`article_id`. Nếu không match được evidence chunk chính xác, evaluation fallback về
document chunk của article đó để run không crash.

| Metric | Ý nghĩa |
| --- | --- |
| `recall_at_5`, `recall_at_10` | Relevant evidence chunk có nằm trong top K không |
| `precision_at_5`, `precision_at_10` | Tỷ lệ top K chunks là relevant |
| `mrr` | Reciprocal rank của relevant chunk đầu tiên |
| `ndcg_at_5`, `ndcg_at_10` | Chất lượng ranking với binary relevance |
| `event_type_coverage_at_5/10` | Tỷ lệ gold event type được cover trong top K |
| `event_evidence_coverage_at_5/10` | Tỷ lệ gold event có evidence trong top K |
| `unique_event_types_at_5/10` | Số event type xuất hiện trong top K |
| `dominance_ratio_at_5/10` | Mức một event type áp đảo top K |

## Error Analysis

`online_retrieval_error_analysis.md` nên trả lời:

- config nào recall thấp;
- event type nào thường bị miss;
- miss do không retrieve đúng article hay retrieve đúng article nhưng sai chunk;
- context có bị generic market text áp đảo không;
- multi-event strategy có cải thiện event coverage không;
- top chunks có thiếu `pattern_refs` không.

File này là tài liệu debug cho M03/M04, không phải báo cáo cuối cùng. Báo cáo cuối
cùng ở M08 có thể tổng hợp lại metrics.

## PostgreSQL Sync

Khi sync, M04 ghi:

| Bảng | Nội dung |
| --- | --- |
| `retrieval_runs` | Một dòng cho mỗi article/config retrieval run |
| `retrieval_run_contexts` | Các context trong run, gồm rank, chunk, score, context JSON và pattern refs |

M06 sync extraction sẽ lưu `retrieval_run_id` và `context_chunk_ids` để nối extraction
output về retrieval context. Đây là đường trace chính khi cần giải thích vì sao một
event được model trích xuất.

## CLI

Chạy online retrieval:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval run-batch `
  --articles-path data/processed/articles_clean.jsonl `
  --chunks-path data/processed/chunks.jsonl `
  --bm25-index-path data/retrieval/bm25_index.pkl `
  --embeddings-path data/retrieval/chunk_embeddings.jsonl `
  --gold-path data/labels/events_gold.jsonl `
  --output-path data/retrieval/online_contexts.jsonl `
  --logs-path data/retrieval/online_retrieval_logs.jsonl `
  --metrics-path reports/evaluation/online_retrieval_metrics.csv `
  --error-analysis-path reports/evaluation/online_retrieval_error_analysis.md `
  --config metadata_aware_hybrid `
  --max-contexts 10 `
  --llm-rerank-mode student_env `
  --llm-rerank-top-n 15
```

`student_env` yêu cầu cấu hình `STUDENT_LLM_PROVIDER`, `STUDENT_LLM_MODEL`,
`STUDENT_LLM_BASE_URL` và `STUDENT_LLM_API_KEY`. Khi smoke test local không muốn gọi
API, dùng `--llm-rerank-mode deterministic` hoặc `--llm-rerank-mode off`.

Sync retrieval runs:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval sync-postgres `
  --retrieval-results-path data/retrieval/online_contexts.jsonl
```

Các command ad hoc `query` và `query-article` vẫn còn để debug, nhưng graph run dùng
`run-batch`.

## Failure Cases

| Trường hợp | Hành vi mong muốn |
| --- | --- |
| Thiếu chunks | Fail rõ ở M04, vì không có corpus retrieval |
| Thiếu embeddings | Dense/hybrid strategy không thể chạy đúng, không sinh fake score |
| Thiếu BM25 index | BM25/hybrid strategy fail rõ |
| Không có gold labels | Vẫn sinh contexts, metrics có thể rỗng |
| Không retrieve được context | Ghi context list rỗng và log lại |
| Context không có pattern refs | Vẫn hợp lệ, M06 chạy với context text nhưng không có matched patterns |
| Evidence span không match chunk | Evaluation fallback về document chunk cùng article |

## Tiêu Chí Hoàn Tất

- M04 ghi `online_contexts.jsonl` cho selected articles.
- Mỗi context có `chunk_id`, `article_id`, `rank`, `score`, `text`, metadata và score breakdown.
- Context metadata mang `pattern_refs` đã gắn trên chunk.
- Retrieval metrics được ghi khi có gold labels.
- `retrieval_runs` và `retrieval_run_contexts` sync được mà không cần M06.
- M06 chạy được từ `retrieval_results_path` mà không tự retrieve.

## Tests

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_retrieval_reranking.py tests/test_online_extraction_workflow.py
```
