# Embedding Retrieval Workflow

## Mục tiêu

Tìm các bài báo và pattern liên quan nhất với bài báo đầu vào để hỗ trợ model 8B trích xuất sự kiện chính xác hơn.

Workflow này không quyết định output cuối cùng. Nó chỉ tạo context có chất lượng cao cho bước LLM extraction.

## Input

Bài báo mới đã được làm sạch:

```json
{
  "article_id": "input_001",
  "title": "HPG trúng thầu dự án cung cấp thép cho ...",
  "text": "Nội dung bài báo đầy đủ...",
  "source_url": "https://example.com/news",
  "published_at": "2026-06-13T08:00:00+07:00"
}
```

Corpus đã index:

```json
{
  "article_id": "cafef_hpg_20260115_001",
  "chunk_id": "cafef_hpg_20260115_001_c03",
  "text": "Đoạn văn bản chunk...",
  "metadata": {
    "ticker": "HPG",
    "source": "cafef",
    "event_type_hint": "CONTRACT"
  },
  "embedding": [0.01, -0.03, 0.18]
}
```

## Output

Danh sách context ứng viên:

```json
{
  "query_article_id": "input_001",
  "retrieved_contexts": [
    {
      "rank": 1,
      "article_id": "cafef_hpg_20260115_001",
      "chunk_id": "cafef_hpg_20260115_001_c03",
      "score": 0.87,
      "score_breakdown": {
        "vector_score": 0.81,
        "keyword_score": 0.12,
        "ticker_bonus": 0.05
      },
      "text": "Đoạn liên quan...",
      "metadata": {
        "source": "cafef",
        "ticker": "HPG"
      }
    }
  ]
}
```

## Công nghệ

- Cloudflare Workers AI embedding endpoint đã được setup.
- PostgreSQL + pgvector là vector backend mặc định lâu dài.
- FAISS dùng làm vector search baseline trong ablation.
- BM25 cho lexical search.
- PostgreSQL lưu metadata bài báo, chunk, embeddings và run logs.
- Python scripts cho batch indexing.
- LangGraph dùng khi retrieval là một node trong online extraction workflow.
- Optional: reranker nhỏ, cross-encoder reranker hoặc LLM reasoning rerank.

## Cách hoạt động

### Bước 1: Structure-aware chunking

Bài báo dài được chia thành chunk để retrieval chính xác hơn.

Không chunk cố định tùy tiện. Quy tắc v1:

- Mỗi chunk khoảng 300-600 từ tiếng Việt.
- Có overlap 50-100 từ.
- Luôn giữ `article_id`, `chunk_id`, `title`, `source`, `published_at`.
- Nếu bài ngắn dưới 700 từ, có thể dùng một chunk duy nhất.
- Ưu tiên ranh giới paragraph, bullet và section.
- Không tách đôi câu chứa số tiền, ngày tháng, tên dự án hoặc tên đối tác.
- Title và sapo được lưu trong metadata của mọi chunk.

Ngoài chunk cấp paragraph, hệ thống nên lưu thêm:

| Cấp | Mục đích |
| --- | --- |
| Document-level | Tìm bài liên quan tổng thể |
| Section-level | Tìm vùng nội dung liên quan |
| Paragraph-level | Lấy evidence span cụ thể |

### Bước 2: Embedding

Mỗi chunk được gửi qua Cloudflare embedding model để lấy vector.

Yêu cầu:

- Lưu cả vector và metadata.
- Cache embedding theo `content_hash` để tránh gọi lại API.
- Log model name và embedding version.

### Bước 3: Keyword Signal

Tạo điểm keyword dựa trên các cụm từ sự kiện:

```text
trúng thầu, ký hợp đồng, phát hành, tăng vốn, mua lại,
sáp nhập, bổ nhiệm, miễn nhiệm, khởi công, mở rộng,
bị phạt, bị điều tra, kiện tụng, cấp phép, chấp thuận
```

Keyword không thay thế embedding, chỉ là tín hiệu bổ sung để tránh bỏ sót sự kiện có từ khóa rõ.

### Bước 4: Query rewriting and decomposition

Từ bài báo đầu vào, tạo nhiều query để tránh phụ thuộc vào một biểu diễn duy nhất.

Ví dụ query:

```json
[
  {
    "name": "ticker_event_query",
    "text": "HPG trúng thầu hợp đồng dự án",
    "weight": 1.0
  },
  {
    "name": "company_query",
    "text": "Hoa Phat ký hợp đồng cung cấp thép",
    "weight": 0.8
  },
  {
    "name": "event_type_query",
    "text": "doanh nghiệp trúng thầu hợp đồng lớn",
    "weight": 0.6
  }
]
```

Các sub-query nên tách theo:

- cùng công ty/ticker
- cùng loại sự kiện
- cùng trigger action
- cùng dự án/đối tác nếu bài có nêu

Với bài có nhiều event type, strategy `multi_event_aware_hybrid` không query tất cả
taxonomy enum. Nó chỉ tạo query intent riêng cho các event type đã được phát hiện
trong `event_type_hints` của bài đầu vào. Chi tiết:
[`multi-event-aware-retrieval.md`](multi-event-aware-retrieval.md).

### Bước 5: Hybrid Retrieval

Tính điểm tổng:

```text
final_score = alpha * vector_score
            + beta * keyword_score
            + gamma * ticker_bonus
            + delta * recency_bonus
```

Mặc định v1:

```json
{
  "alpha": 0.55,
  "beta": 0.25,
  "gamma": 0.15,
  "delta": 0.05
}
```

Nếu không xác định được ticker, `ticker_bonus=0`.

Metadata-aware retrieval:

- Filter mềm theo ticker/company nếu có.
- Ưu tiên source đáng tin cậy.
- Ưu tiên thời gian gần nếu cùng loại sự kiện.
- Không loại tuyệt đối bài thiếu ticker, vì nhiều bài chỉ có tên công ty.

### Bước 6: Multi-stage retrieval

Retrieval nên chạy nhiều tầng:

| Stage | Mục tiêu | Output |
| --- | --- | --- |
| Stage 1 | Retrieve rộng bằng BM25 + dense | top 50 |
| Stage 2 | Metadata/rule rerank | top 20 |
| Stage 3 | LLM reasoning rerank hoặc reranker nhỏ | top 3-5 |
| Stage 4 | Dedup và build context pack | final context |

Với `multi_event_aware_hybrid`, Stage 1 lấy rộng hơn và final context có adaptive
budget: 5 context cho single-event, 8 context cho 2 event type và tối đa 10 context
cho từ 3 event type. Online extraction vẫn có `max_contexts` để cắt lớp cuối.

### Bước 7: Reranking

Sau khi lấy top 20 chunk, rerank để chọn top 3-5 context đưa vào LLM.

Các phương án thí nghiệm:

- `vector_only`: chỉ cosine similarity.
- `hybrid_score`: vector + keyword + metadata bonus.
- `llm_filter`: model 8B đọc ngắn từng candidate và trả `relevant/not_relevant`.
- `rule_aware_rerank`: ưu tiên chunk có event keyword và ticker/company trùng.
- `llm_reasoning_rerank`: model 8B đọc toàn văn bài ứng viên, chạy một quy trình lập luận có cấu trúc để chấm mức liên quan.
- `multi_event_aware_hybrid`: tách query theo event type đã detect; chunk dùng coverage/MMR và pattern dùng coverage selection để tránh context/few-shot bị một event áp đảo.
- `trainable_reranker`: optional reranker nhỏ train trên AI-generated relevance labels nếu có đủ dữ liệu.

#### `llm_reasoning_rerank`

Phương án này dùng sau khi đã có top 10-20 ứng viên từ `hybrid_score`. Khác với `llm_filter` chỉ trả `relevant/not_relevant`, `llm_reasoning_rerank` yêu cầu LLM đọc toàn văn bài ứng viên và trả điểm dựa trên các câu hỏi logic.

Mục tiêu là lọc ra bài thật sự liên quan về **cùng loại sự kiện doanh nghiệp**, không chỉ giống từ khóa hoặc giống embedding.

Prompt rerank nên yêu cầu model kiểm tra:

1. Bài ứng viên có chứa sự kiện doanh nghiệp cụ thể không?
2. Sự kiện đó thuộc event type nào trong taxonomy?
3. Actor chính là công ty nào, có trùng hoặc liên quan với bài đầu vào không?
4. Nguyên nhân hoặc bối cảnh sự kiện là gì?
5. Trong bài có các dấu hiệu như hợp đồng, phê duyệt, tăng vốn, thay lãnh đạo, kiện tụng, mở rộng dự án không?
6. Evidence span nào chứng minh bài ứng viên liên quan?
7. Bài ứng viên có chỉ là phân tích chung/tin giá/tin thị trường không?
8. Mức liên quan cuối cùng với bài đầu vào là `HIGH`, `MEDIUM`, `LOW`, hay `IRRELEVANT`?

Output trung gian của reranker:

```json
{
  "candidate_article_id": "cafef_hpg_20260115_001",
  "has_corporate_event": true,
  "candidate_event_type": "CONTRACT",
  "same_or_related_company": true,
  "same_or_related_event_type": true,
  "reasoning_summary": "Cả hai bài đều nói về HPG và sự kiện ký hợp đồng/trúng thầu có giá trị cụ thể.",
  "evidence_span": "HPG đã trúng gói thầu trị giá ...",
  "relevance_label": "HIGH",
  "relevance_score": 0.92
}
```

Quy đổi điểm:

| relevance_label | relevance_score gợi ý |
| --- | --- |
| `HIGH` | 0.85-1.00 |
| `MEDIUM` | 0.60-0.84 |
| `LOW` | 0.30-0.59 |
| `IRRELEVANT` | 0.00-0.29 |

Điểm cuối có thể kết hợp với hybrid score:

```text
final_rerank_score = 0.40 * hybrid_score + 0.60 * llm_relevance_score
```

Lưu ý:

- Chỉ chạy trên top 10-20 ứng viên để kiểm soát token và chi phí.
- Nếu bài ứng viên quá dài, đưa title + đoạn mở đầu + các đoạn có keyword sự kiện + metadata; nếu vẫn còn token thì thêm toàn văn.
- Nếu LLM không đưa được evidence span, hạ `relevance_score` hoặc loại candidate.
- Strategy này phù hợp để làm thí nghiệm so sánh với `vector_only`, `hybrid_score` và `rule_aware_rerank`.

## Flow Metrics

| Metric | Ý nghĩa | Cách đo |
| --- | --- | --- |
| Recall@K | Gold evidence có nằm trong top K không | Số bài/chunk đúng trong top K |
| Precision@K | Top K có bao nhiêu context thật sự liên quan | AI-generated gold relevance hoặc AI judge |
| MRR | Rank của context đúng đầu tiên | Mean reciprocal rank |
| nDCG@K | Chất lượng ranking | Dùng relevance 0/1/2 |
| Rerank agreement | LLM rerank có đồng ý với AI-generated gold relevance không | agreement rate hoặc Cohen's kappa nếu có nhãn |
| Retrieval latency | Thời gian truy hồi | ms/query |
| Embedding cost | Chi phí embedding | cost/article hoặc cost/chunk |
| Rerank token cost | Chi phí token cho LLM rerank | tokens/query |

## Experiment Matrix

| Run | Chunking | Embedding | Retrieval | Rerank |
| --- | --- | --- | --- | --- |
| R1 | article-level | Cloudflare | dense only | none |
| R2 | paragraph chunks | Cloudflare | dense only | none |
| R3 | paragraph chunks | Cloudflare | BM25 only | none |
| R4 | paragraph chunks | Cloudflare | hybrid | none |
| R5 | hierarchical chunks | BGE-M3/E5/GTE | hybrid + metadata | rule-aware |
| R6 | hierarchical chunks | best embedding | hybrid + metadata | LLM reasoning |
| R7 | hierarchical chunks | best embedding | hybrid + metadata | trainable reranker optional |

## Acceptance Criteria v1

- `Recall@10 >= 0.80` trên tập evaluation có evidence.
- Top 5 context không vượt quá giới hạn token của model 8B.
- Retrieval latency đủ cho demo, mục tiêu dưới 3 giây/article với corpus nhỏ.
- Mỗi context trả về phải có `article_id`, `chunk_id`, `score`, `text`, `metadata`.

## Failure Cases

| Case | Cách xử lý |
| --- | --- |
| Bài đầu vào quá dài | Chunk trước khi embedding |
| Cloudflare API lỗi | Retry, fallback dùng cache hoặc báo lỗi rõ |
| Không tìm được context tốt | Vẫn chạy extraction zero-shot nhưng log `retrieval_empty=true` |
| Context trùng nhau | Dedup theo `article_id` và overlap text |
| Top context sai chủ đề | Rerank bằng keyword/ticker/LLM filter |

## Artifact

```text
data/
  vector_store/
    index.faiss
    metadata.jsonl
  retrieval/
    retrieval_logs.jsonl
```

Mỗi log retrieval nên lưu:

```json
{
  "run_id": "20260613_001",
  "query_article_id": "input_001",
  "retrieval_config": "hybrid_v1",
  "top_k": 10,
  "results": []
}
```
