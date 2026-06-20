# M04: Retrieval and Reranking Experiments

## Mục tiêu

Milestone này xây dựng lớp retrieval/reranking trên artifacts của M03 để chọn context tốt nhất cho extraction. Trọng tâm là Advanced RAG cho bài toán NLP trích xuất sự kiện:

- Không chỉ semantic search.
- Có BM25 lexical retrieval.
- Có dense retrieval từ embedding artifacts.
- Có hybrid scoring.
- Có metadata-aware scoring.
- Có rule-aware rerank.
- Có LLM reasoning rerank prompt/scaffold.
- Có retrieval logs và metrics định lượng.

## Vai trò trong project

M04 là bước quyết định chất lượng context trước khi đưa vào model 8B ở M06:

- Nếu retrieval sai, extraction có thể sinh bảng đúng format nhưng sai evidence.
- Nếu retrieval chỉ dựa dense search, hệ thống dễ lấy bài giống chủ đề nhưng khác sự kiện.
- Nếu retrieval chỉ dựa keyword, hệ thống dễ bỏ sót cách diễn đạt khác.
- Vì vậy M04 so sánh nhiều strategy và ghi rõ score breakdown để biết thành phần nào thật sự giúp tăng độ chính xác.

## Input

```text
data/processed/chunks.jsonl
data/retrieval/bm25_index.pkl
data/retrieval/chunk_embeddings.jsonl
data/labels/events_gold.jsonl
```

Các input này được tạo từ:

- M03: chunks, BM25, embeddings.
- M02: AI-generated gold labels đã pass auto validation.

## Output

```text
data/retrieval/retrieval_logs.jsonl
reports/evaluation/retrieval_metrics.csv
reports/evaluation/retrieval_error_analysis.md
```

Các output này là experiment artifacts, không cần commit.

## Công nghệ

| Thành phần | Công nghệ | Dùng để làm gì |
| --- | --- | --- |
| Query decomposition | `finevent.retrieval.querying` | Tạo nhiều sub-query theo title, ticker, company, event type |
| BM25 retrieval | `finevent.rag.bm25` | Lexical baseline bắt keyword sự kiện rõ |
| Dense retrieval | Embedding artifacts từ M03 | Semantic baseline dựa trên vector similarity |
| Hybrid scoring | `finevent.retrieval.engine` | Kết hợp dense, BM25, metadata, recency/source |
| Metadata-aware scoring | ticker/company/event keyword/event type overlap | Ưu tiên context cùng công ty và cùng loại sự kiện |
| Rule-aware rerank | rule score deterministic | Cộng/trừ điểm theo event keyword, generic market text, evidence-like chunk |
| LLM reasoning rerank | prompt scaffold + deterministic local judgment | Dùng LLM đọc top candidates và chấm relevance theo logic sự kiện |
| Evaluation | stdlib CSV/math | Tính Recall@K, Precision@K, MRR, nDCG |
| CLI | `python -m finevent.retrieval` | Query thủ công, query theo article, compare strategy, render rerank prompt |

## Retrieval Configs

M04 hiện có các config mặc định:

| Config | Dense | BM25 | Metadata | Recency/source | Rule | LLM | Mục đích |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `bm25_only` | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | Lexical baseline |
| `dense_only` | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | Semantic baseline |
| `hybrid` | 0.55 | 0.45 | 0.00 | 0.00 | 0.00 | 0.00 | Dense + lexical |
| `metadata_aware_hybrid` | 0.45 | 0.30 | 0.20 | 0.05 | 0.00 | 0.00 | Hybrid có ticker/company/event metadata |
| `rule_aware_rerank` | 0.40 | 0.25 | 0.20 | 0.05 | 0.10 | 0.00 | Thêm rule rerank deterministic |
| `llm_reasoning_rerank` | 0.25 | 0.15 | 0.10 | 0.00 | 0.10 | 0.40 | Scaffold cho LLM rerank top candidates |

## Query decomposition

Từ một article, hệ thống tạo nhiều query:

| Query type | Nội dung |
| --- | --- |
| `title` | Title gốc của bài |
| `ticker_event` | Ticker + event keywords + title |
| `company_event` | Company name + event keywords |
| `event_type` | Event type/subtype hints + event keywords |
| `body_fallback` | 80 từ đầu nếu thiếu title/metadata |

Ví dụ:

```json
[
  {
    "query_type": "ticker_event",
    "text": "HPG khoi cong mo rong nha may HPG khoi cong du an nha may moi",
    "weight": 1.0
  },
  {
    "query_type": "event_type",
    "text": "EXPANSION NEW_FACTORY khoi cong mo rong nha may moi",
    "weight": 0.65
  }
]
```

## Score breakdown

Mọi candidate đều có score breakdown:

```json
{
  "dense_score": 0.779751,
  "bm25_score": 1.0,
  "metadata_score": 0.75,
  "recency_score": 0.05,
  "rule_score": 0.0,
  "matched_query_types": ["manual"],
  "retrieval_config": "metadata_aware_hybrid",
  "query_count": 1
}
```

Điểm cuối:

```text
score =
  dense_weight * dense_score
+ bm25_weight * bm25_score
+ metadata_weight * metadata_score
+ recency_weight * recency_score
+ rule_weight * rule_score
+ llm_weight * llm_relevance_score
```

## LLM reasoning rerank

M04 chưa gọi API LLM trực tiếp để tránh phụ thuộc model/token trong test. Thay vào đó có:

- `build_llm_reasoning_rerank_prompt`: render prompt chuẩn để đưa top candidates cho LLM.
- `apply_llm_reasoning_judgments`: nhận JSON judgments từ LLM và trộn lại điểm.
- `deterministic_reasoning_judgments`: stand-in rẻ để test/demo local.

Prompt yêu cầu LLM kiểm tra:

- candidate có corporate event cụ thể không.
- actor/company có cùng hoặc liên quan không.
- event type/subtype có cùng hoặc liên quan không.
- evidence span nào chứng minh relevance.
- candidate có chỉ là tin giá/nhận định thị trường chung không.
- relevance label: `HIGH`, `MEDIUM`, `LOW`, `IRRELEVANT`.
- relevance score trong `[0, 1]`.

Lệnh render prompt:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval llm-rerank-prompt `
  --query "HPG khoi cong nha may" `
  --top-k 10
```

## CLI usage

### Query thủ công

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval query `
  --query "HPG khoi cong nha may" `
  --ticker HPG `
  --event-keyword "khoi cong" `
  --event-type EXPANSION `
  --config metadata_aware_hybrid `
  --top-k 5
```

### Query theo article đã ingest

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval query-article `
  --articles-path data\processed\articles_clean.jsonl `
  --article-id cafef_833adef5f3d9 `
  --config rule_aware_rerank `
  --top-k 5
```

### So sánh retrieval strategies

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.retrieval compare `
  --gold-path data\labels\events_gold.jsonl `
  --logs-path data\retrieval\retrieval_logs.jsonl `
  --metrics-path reports\evaluation\retrieval_metrics.csv `
  --error-analysis-path reports\evaluation\retrieval_error_analysis.md
```

Có thể giới hạn config:

```powershell
python -m finevent.retrieval compare --config bm25_only --config hybrid
```

## Evaluation

Ground truth trong M04 lấy từ `events_gold.jsonl`:

- Mỗi event tạo một eval case.
- `evidence_span` được match vào paragraph/section/document chunks cùng `article_id`.
- Relevant chunks là chunks chứa evidence span.
- Nếu không match evidence span, fallback về document chunk của article đó để không làm crash run.

Metrics:

| Metric | Ý nghĩa |
| --- | --- |
| `recall_at_5`, `recall_at_10` | Relevant evidence có nằm trong top K không |
| `precision_at_5`, `precision_at_10` | Top K có bao nhiêu relevant chunks |
| `mrr` | Rank của relevant chunk đầu tiên |
| `ndcg_at_5`, `ndcg_at_10` | Ranking quality với binary relevance |
| `first_relevant_rank` | Rank đầu tiên có evidence đúng |

## Kiểm thử

Test file:

```text
tests/test_retrieval_reranking.py
```

Chạy:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests\test_retrieval_reranking.py
```

Test bao phủ:

- Query decomposition dùng title/ticker/company/event metadata.
- 4 strategy chính trả đúng format.
- Score breakdown có dense/BM25/metadata.
- Rule-aware và LLM reasoning rerank giữ relevant event chunk ở top.
- LLM prompt có candidate schema.
- Comparison runner ghi logs, metrics CSV và error analysis.

## Smoke result hiện tại

Trên fixture HPG:

```text
retrieval query "HPG khoi cong nha may"
rank 1: cafef_833adef5f3d9_paragraph_0000
```

Comparison hiện chạy 6 config, 1 eval case:

```text
bm25_only              Recall@5 = 1.0
dense_only             Recall@5 = 1.0
hybrid                 Recall@5 = 1.0
metadata_aware_hybrid  Recall@5 = 1.0
rule_aware_rerank      Recall@5 = 1.0
llm_reasoning_rerank   Recall@5 = 1.0
```

Vì corpus fixture chỉ có một bài, kết quả này chỉ xác nhận pipeline đúng. Khi có corpus thật, bảng này mới dùng để chọn config production.

## Done Criteria

- Có module `finevent.retrieval`.
- Có ít nhất 4 retrieval configs để so sánh.
- Có query decomposition.
- Có BM25-only, dense-only, hybrid, metadata-aware hybrid.
- Có rule-aware rerank.
- Có LLM reasoning rerank prompt/scaffold.
- Có retrieval logs.
- Có `retrieval_metrics.csv`.
- Có `retrieval_error_analysis.md`.
- Có test M04 pass.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Dense search trả bài giống chủ đề nhưng sai sự kiện | Tăng BM25/event keyword/metadata/rule weight |
| BM25 bỏ sót diễn đạt khác | Kết hợp dense retrieval |
| Metadata filter loại nhầm bài | Dùng soft boost, không hard filter sớm |
| Nhiều chunk trùng nhau | Dedup theo `chunk_hash`, giới hạn số chunk mỗi article |
| LLM rerank tốn chi phí | Chỉ rerank top 10-20, log token/cost ở milestone sau |
| Gold evidence không match chunk | Kiểm tra chunking M03 hoặc fallback document chunk để debug |
