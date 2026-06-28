# Workflow Retrieval Bằng Embedding

Workflow này mô tả cách FinEvent retrieve evidence chunks cho extraction. Thiết kế
hiện tại chỉ retrieve chunks. Pattern records được gắn vào chunks trong M03 và đi
cùng chunks qua M04 vào prompt M06.

## Chuẩn Bị Offline

M03 tạo các retrieval artifacts:

```text
data/processed/chunks.jsonl
data/processed/chunk_patterns.jsonl
data/retrieval/chunk_embeddings.jsonl
data/retrieval/bm25_index.pkl
data/vector_store/
data/patterns/patterns.jsonl
```

Mỗi chunk giữ metadata cần cho retrieval và prompting:

```json
{
  "chunk_id": "article_001_p02",
  "article_id": "article_001",
  "chunk_level": "paragraph",
  "text": "Evidence-bearing paragraph...",
  "metadata": {
    "source": "cafef",
    "tickers": ["HPG"],
    "event_type_hints": ["CONTRACT"]
  },
  "pattern_refs": [
    {
      "pattern_id": "pattern_article_001_contract",
      "event_type": "CONTRACT",
      "evidence_span": "..."
    }
  ]
}
```

Không có retrieval flow vector riêng cho patterns.

## Mục Tiêu Của Retrieval

Retrieval trong project này không nhằm trả lời câu hỏi tự do. Nó nhằm chọn evidence
chunks tốt nhất để M06 trích xuất sự kiện có cấu trúc. Vì vậy context tốt cần:

- cùng hoặc liên quan trực tiếp đến article đầu vào;
- chứa event trigger hoặc evidence cụ thể;
- có metadata giúp model hiểu ticker/company/event type;
- không chỉ là tin giá hoặc nhận định thị trường chung;
- nếu có pattern refs thì pattern phải gắn với chunk đó.

Đây là lý do hệ thống không chỉ dùng dense similarity. Tin tài chính có nhiều bài
giống chủ đề nhưng khác sự kiện, nên BM25, metadata và rule signals vẫn rất quan
trọng.

## Online Retrieval

M04 biến input article thành context pack:

1. Load article metadata và text.
2. Build title/ticker/company/event/body queries.
3. Retrieve candidates từ BM25 và dense chunk embeddings.
4. Score candidates bằng dense, lexical, metadata, recency/source và rule signals.
5. Apply strategy selection. Với `multi_event_aware_hybrid`, bước này là coverage/MMR và giữ pool rộng hơn `max_contexts`.
6. Nếu bật `llm_rerank_mode`, chạy listwise LLM rerank như bước xếp hạng cuối cùng trên pool đã được strategy chọn.
7. Cắt theo `max_contexts` và ghi `data/retrieval/online_contexts.jsonl`.

M06 đọc file đó và chọn record khớp `article_id` + `retrieval_config`. Field
`retrieval_config` là tên recipe scoring/rerank M04 đã dùng, không phải lệnh để M06
retrieve lại hoặc chọn một thuật toán đơn lẻ.

## Chunking

M03 chunking có ý thức cấu trúc:

- giữ document, section và paragraph chunks;
- ưu tiên paragraph boundaries;
- paragraph dài được tách theo câu;
- title/source/date/ticker/event hints đi cùng metadata;
- `max_words` giới hạn chunk size;
- `overlap_words` giữ context continuity.

Default graph config:

```text
target_words = 420
max_words = 620
overlap_words = 80
```

## Embeddings

Chunk embeddings được tạo ở M03 bằng provider cấu hình:

- `hash` cho local tests deterministic;
- `cloudflare`, `openai_compatible` hoặc `direct_http` cho external providers.

Embeddings dùng text truy hồi tự nhiên đã normalize từ `chunk.text`, title và metadata
hints như ticker/company/event keyword. Project không dùng VnCoreNLP hoặc bản gạch dưới
để tránh làm nhiễu vector retrieval. Embeddings lưu ở `data/retrieval/chunk_embeddings.jsonl`
và sync vào PostgreSQL khi `sync_postgres=true`.

## BM25 Và Metadata

BM25 tokenizer cũng chạy preprocessing tiếng Việt để query và document cùng cách normalize.
BM25 giúp bắt các trigger words như:

```text
trúng thầu, ký hợp đồng, phát hành, tăng vốn, mua lại,
sáp nhập, bổ nhiệm, miễn nhiệm, khởi công, mở rộng,
bị phạt, điều tra, kiện tụng, cấp phép, chấp thuận
```

Metadata giúp phân biệt bài cùng chủ đề nhưng khác actor hoặc khác event:

- ticker overlap;
- company name overlap;
- event keyword overlap;
- event type/subtype hints;
- source/recency.

Dense retrieval tốt cho diễn đạt khác nhau, nhưng metadata giúp tránh lấy bài chỉ
giống ngữ nghĩa chung.

## Query Decomposition

M04 build nhiều query vì một text query duy nhất dễ thiếu tín hiệu trong tin tài
chính:

| Query type | Mục đích |
| --- | --- |
| `title` | Giữ framing trực tiếp của bài |
| `ticker_event` | Nhấn mạnh stock ticker + event triggers |
| `company_event` | Bắt bài dùng tên công ty thay vì ticker |
| `event_type` | Retrieve event type/subtype tương tự |
| `body_fallback` | Giữ retrieval usable khi title/metadata yếu |

`multi_event_aware_hybrid` thêm một query cho mỗi event type phát hiện trong
`event_type_hints`. Nó không enumerate toàn bộ taxonomy.

## Scoring

Final candidate score là weighted blend của:

- dense similarity;
- BM25 score;
- metadata overlap;
- recency/source signal;
- deterministic rule score;
- optional listwise LLM relevance score/rank khi M04 bật LLM rerank.

Score breakdown được lưu cùng context để phân tích lỗi sau run.

## Output Và Trace

M04 output giữ đủ thông tin để debug:

| Field | Dùng để làm gì |
| --- | --- |
| `rank` | Context vào prompt theo thứ tự nào |
| `score` | Điểm tổng hợp cuối |
| `score_breakdown` | Biết tín hiệu nào đẩy context lên |
| `chunk_id` | Truy ngược chunk trong M03 artifact/DB |
| `article_id` | Biết context đến từ article nào |
| `metadata` | Ticker/source/event hints/pattern refs |
| `text` | Evidence text đi vào M06 |

Nếu M06 output sai, trace nên đi ngược:

```text
prediction -> extraction_run.context_chunk_ids -> retrieval_run_contexts -> chunk text/pattern_refs
```

## Reranking Strategies

| Strategy | Cách dùng |
| --- | --- |
| `bm25_only` | Kiểm tra lexical trigger coverage |
| `dense_only` | Kiểm tra semantic retrieval quality |
| `hybrid` | Kết hợp lexical và dense signals |
| `metadata_aware_hybrid` | Strategy cân bằng mặc định |
| `rule_aware_rerank` | Đẩy evidence-like chunks lên, phạt generic market text |
| `llm_reasoning_rerank` | Recipe ablation có LLM relevance slot |
| `multi_event_aware_hybrid` | Giữ coverage khi một bài có nhiều event type |

M04 production mặc định dùng listwise rerank qua `llm_rerank_mode=student_env`.
Đây là bước xếp hạng cuối cùng của M04, chạy sau scoring và sau strategy selection.
Với `multi_event_aware_hybrid`, coverage/MMR vẫn chạy trước để giữ đủ event intents;
pool đưa vào LLM được nới rộng tối thiểu theo `llm_rerank_top_n`, rồi LLM mới lọc/xếp
hạng lần cuối trước khi M04 cắt theo `max_contexts`. Prompt đưa top candidates vào
cùng một lần gọi LLM, kèm title/source/published date, document preview, chunk text
ngắn, score breakdown và pattern refs compact. Không đưa nguyên toàn bộ bài báo gốc
của từng chunk vào prompt. Model trả `ranked_candidate_ids` và optional `judgments`;
hệ thống lưu `llm_rank`, `llm_relevance_score` và `llm_reasoning_summary` trong score
breakdown.

## Context Pack

Output M04 được thiết kế để M06 dùng trực tiếp:

```json
{
  "article_id": "article_001",
  "retrieval_config": "metadata_aware_hybrid",
  "contexts": [
    {
      "rank": 1,
      "chunk_id": "article_001_p02",
      "score": 0.91,
      "text": "Evidence-bearing chunk...",
      "metadata": {
        "pattern_refs": []
      }
    }
  ]
}
```

M06 giới hạn số context bằng `max_contexts`. Text chỉ bị trim thêm khi các config
`max_article_chars`, `max_context_chars`, `max_pattern_output_chars` hoặc
`max_prompt_chars` được đặt thành số dương; mặc định `0` là không giới hạn.

## Metrics

Khi có gold labels, M04 đánh giá evidence retrieval:

- Recall@K;
- Precision@K;
- MRR;
- nDCG@K;
- event type coverage;
- event evidence coverage;
- unique event types;
- dominance ratio.

Metrics được ghi vào `reports/evaluation/online_retrieval_metrics.csv`.

## Failure Handling

| Case | Behavior |
| --- | --- |
| Thiếu embeddings | Dense score không chạy được; run fail rõ nếu file bắt buộc vắng |
| Thiếu BM25 index | BM25 strategy không chạy; graph step fail thay vì sinh context giả |
| Không retrieve được context | M04 ghi context list rỗng và log lại; M06 chỉ chạy zero-context nếu config cho phép |
| Thiếu gold labels | Retrieval vẫn chạy; metrics rỗng hoặc bị skip |
| Evidence span không match chunk | Evaluation fallback về document chunk của article đó |

## Kiểm Tra

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_retrieval_reranking.py tests/test_rag_preparation.py
```
