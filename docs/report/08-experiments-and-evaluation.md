# 8. Experiments and Evaluation

## Mục tiêu

Trình bày kế hoạch thí nghiệm và metric để chứng minh hệ thống hiệu quả hơn baseline.

## Nhóm thí nghiệm

### 1. Prompting baseline

So sánh:

- zero-shot direct prompt.
- schema-only prompt.
- schema + taxonomy prompt.

Metric:

- JSON validity.
- event detection F1.
- event type macro-F1.
- hallucination rate.

### 2. Retrieval strategy

So sánh:

- no retrieval.
- BM25 only.
- dense only.
- hybrid.
- hybrid + metadata.
- hybrid + LLM reasoning rerank.

Metric:

- Recall@K.
- Precision@K.
- MRR.
- nDCG.
- end-to-end event F1.

### 3. Chunking strategy

So sánh:

- article-level.
- fixed chunk.
- paragraph-aware.
- structure-aware.
- hierarchical.

Metric:

- retrieval Recall@K.
- evidence match.
- token cost.

### 4. Embedding model comparison

So sánh:

- Cloudflare embedding.
- BGE-M3.
- multilingual E5.
- GTE multilingual.
- Vietnamese embedding model nếu có.

Metric:

- Recall@5/10.
- MRR.
- nDCG.
- latency/cost.

### 5. Label representation

So sánh:

- flat event type.
- event type + subtype.
- multi-label event attributes.

Metric:

- event type macro-F1.
- subtype accuracy.
- Hamming loss.
- multi-label micro/macro-F1.

### 6. Verification ablation

So sánh:

- no verification.
- schema only.
- schema + evidence.
- schema + evidence + self-verification.

Metric:

- hallucination rate.
- evidence coverage.
- event recall.
- JSON validity.

## Bảng kết quả cần có

### Retrieval table

| Run | Chunking | Embedding | Retrieval | Rerank | Recall@5 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### Extraction table

| Run | Retrieval | Pattern | Verification | Event F1 | Type F1 | JSON valid | Hallucination |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### Ablation table

| Component removed | Metric drop | Kết luận |
| --- | --- | --- |
| Retrieval | TBD | TBD |
| Pattern | TBD | TBD |
| Verification | TBD | TBD |

## Error analysis

Phân loại lỗi:

- wrong ticker.
- wrong event type.
- missed event.
- over-extraction.
- unsupported argument.
- bad evidence.
- invalid JSON.

Mỗi loại lỗi nên có ví dụ và cách cải thiện.

## Kết luận thí nghiệm cần rút ra

Báo cáo nên trả lời:

1. Cấu hình retrieval nào tốt nhất?
2. Pattern library có cải thiện extraction không?
3. Verification giảm hallucination bao nhiêu?
4. Cấu trúc nhãn nào phù hợp nhất với dữ liệu v1?
5. Workflow có tốt hơn prompt trực tiếp không?

