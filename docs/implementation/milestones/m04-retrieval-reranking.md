# M4: Retrieval and Reranking Experiments

## Mục tiêu

Xây và đánh giá nhiều chiến lược retrieval/reranking để chọn context tốt nhất cho extraction. Milestone này là phần trọng tâm Advanced RAG: không chỉ semantic search, mà có BM25, metadata-aware retrieval, query rewriting, multi-stage retrieval và LLM reasoning rerank.

## Input

```text
data/processed/chunks.jsonl
PostgreSQL pgvector indexes
data/retrieval/bm25_index.pkl
data/labels/events_gold.jsonl
```

## Output

```text
data/retrieval/retrieval_logs.jsonl
reports/evaluation/retrieval_metrics.csv
reports/evaluation/retrieval_error_analysis.md
```

## Công nghệ

- pgvector dense retrieval.
- BM25 lexical retrieval.
- Hybrid scoring.
- Metadata filter/boost.
- Rule-aware rerank.
- LLM reasoning rerank.
- pandas/numpy để tính Recall@K, MRR, nDCG.

## Cách triển khai chi tiết

### Bước 1: Tạo query object

Từ bài đầu vào hoặc gold event tạo:

- raw query từ title.
- ticker/company query.
- event keyword query.
- event type query.

Ví dụ:

```json
{
  "article_id": "input_001",
  "queries": [
    {"name": "ticker_event", "text": "HPG trúng thầu hợp đồng", "weight": 1.0},
    {"name": "event_type", "text": "doanh nghiệp trúng thầu dự án lớn", "weight": 0.6}
  ]
}
```

### Bước 2: Implement retrieval baselines

Cần có các baseline rõ:

- `bm25_only`.
- `dense_only`.
- `hybrid`.
- `metadata_aware_hybrid`.

Không được chỉ báo cáo một cấu hình retrieval.

### Bước 3: Hybrid scoring

Điểm gợi ý:

```text
score =
  0.45 * dense_score
+ 0.30 * bm25_score
+ 0.15 * ticker_or_company_bonus
+ 0.10 * recency_or_source_bonus
```

Trọng số phải nằm trong config để chạy ablation.

### Bước 4: Rule-aware rerank

Rule cộng/trừ điểm:

- cùng ticker/company: cộng.
- có event keyword trùng: cộng.
- cùng event type hint: cộng.
- chỉ là tin giá/nhận định thị trường: trừ.
- không có evidence span rõ: trừ.

### Bước 5: LLM reasoning rerank

Chỉ chạy trên top 10-20 để tiết kiệm token.

Prompt yêu cầu LLM đọc candidate và trả:

- có corporate event cụ thể không.
- actor chính.
- event type/subtype.
- nguyên nhân/bối cảnh.
- evidence span.
- relevance label.
- relevance score.

LLM rerank không sinh event output cuối; nó chỉ chấm relevance.

### Bước 6: Evaluate retrieval

Ground truth có thể lấy từ:

- evidence article/chunk trong AI-generated gold.
- pattern cùng event type/subtype.
- AI judge relevance cho dev set nếu thiếu nhãn relevance.

Metric:

- Recall@5, Recall@10.
- Precision@K.
- MRR.
- nDCG@K.
- latency.
- token cost nếu dùng LLM rerank.

## Kiểm thử

- Test mỗi retrieval strategy trả đúng format.
- Test score breakdown có đủ dense/BM25/metadata/rerank.
- Test dedup không trả nhiều chunk gần như giống nhau.
- Test config thay đổi top K có tác dụng.

## Done Criteria

- Có ít nhất 4 config retrieval được so sánh.
- Có `retrieval_metrics.csv`.
- Có config mặc định được chọn cho milestone extraction.
- Có phân tích trade-off accuracy/latency/cost.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| Semantic search trả bài giống chủ đề nhưng sai event | Thêm BM25/event keyword và LLM reasoning rerank |
| BM25 bỏ sót câu diễn đạt khác | Kết hợp dense retrieval |
| LLM rerank quá đắt | Chỉ rerank top 10-20 |
| Metadata filter loại nhầm bài | Dùng boost mềm, không filter cứng quá sớm |
