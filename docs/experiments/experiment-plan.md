# Experiment Plan

## Mục tiêu

Thiết kế thí nghiệm đủ chặt để chứng minh workflow có cải thiện độ chính xác, đồng thời đáp ứng yêu cầu SE365 về:

- So sánh nhiều mô hình.
- Thử nhiều cấu trúc nhãn.
- Thử nhiều cách rút trích đặc trưng/retrieval.
- Thử nhiều kỹ thuật Advanced RAG: chunking, embedding, hybrid retrieval, reranking, verification.
- Có đánh giá định lượng.
- Có hướng mở cho loss functions mà không làm lệch khỏi hướng workflow-first.

## Nguyên tắc

- Mỗi thí nghiệm chỉ thay đổi một nhóm yếu tố chính.
- Dùng cùng test set để so sánh.
- Log đầy đủ prompt version, model, retrieval config, pattern config.
- Không chọn cấu hình tốt nhất dựa trên cảm giác.

## Experiment 1: Baseline Prompting

### Mục tiêu

Đo baseline khi không dùng retrieval và không dùng pattern.

### Cấu hình

| Run | Model | Prompt | Retrieval | Pattern |
| --- | --- | --- | --- | --- |
| E1.1 | 8B model A | zero-shot | none | none |
| E1.2 | 8B model A | schema-only | none | none |
| E1.3 | 8B model A | schema + taxonomy | none | none |

### Metrics

- JSON validity rate.
- Event detection F1.
- Event type macro-F1.
- Hallucination rate.

### Kỳ vọng

Prompt có schema + taxonomy tốt hơn zero-shot, nhưng vẫn còn lỗi format và thiếu evidence.

## Experiment 2: Retrieval Strategy

### Mục tiêu

Kiểm tra retrieval có giúp model chọn đúng evidence và giảm hallucination không.

### Cấu hình

| Run | Retrieval |
| --- | --- |
| E2.1 | No retrieval |
| E2.2 | Vector only |
| E2.3 | Keyword only |
| E2.4 | Hybrid vector + keyword + ticker bonus |
| E2.5 | Hybrid + rule-aware rerank |
| E2.6 | Hybrid + LLM reasoning rerank |
| E2.7 | Hybrid + metadata-aware retrieval |
| E2.8 | Hybrid + query rewriting/decomposition + LLM reasoning rerank |

### Metrics

- Recall@K, Precision@K, MRR cho retrieval.
- Event extraction F1 end-to-end.
- Evidence accuracy.
- Latency.
- Rerank token cost nếu dùng LLM reasoning rerank.

### Kết luận cần rút ra

Retrieval nào cân bằng tốt nhất giữa accuracy và chi phí/thời gian.

## Experiment 2A: Chunking Strategy

### Mục tiêu

Chứng minh dữ liệu được xử lý có cấu trúc, không chunk cố định tùy tiện.

### Cấu hình

| Run | Chunking |
| --- | --- |
| E2A.1 | Article-level, không chunk |
| E2A.2 | Fixed-size chunk 500 từ |
| E2A.3 | Paragraph-aware chunking |
| E2A.4 | Structure-aware chunking: title, sapo, paragraph, bullet |
| E2A.5 | Hierarchical chunking: document + section + paragraph |

### Metrics

- Retrieval Recall@K.
- Evidence exact/partial match.
- End-to-end event F1.
- Average chunks/article.
- Token cost.

### Kết luận cần rút ra

Structure-aware hoặc hierarchical chunking có giúp tìm evidence tốt hơn fixed chunk không.

## Experiment 2B: Embedding Model Comparison

### Mục tiêu

So sánh nhiều embedding model thay vì dùng duy nhất một embedding mặc định.

### Cấu hình

| Run | Embedding model |
| --- | --- |
| E2B.1 | Cloudflare embedding hiện có |
| E2B.2 | BGE-M3 |
| E2B.3 | Multilingual E5 |
| E2B.4 | GTE multilingual |
| E2B.5 | Vietnamese embedding model nếu có |

### Metrics

- Recall@5, Recall@10.
- MRR.
- nDCG@10.
- Embedding latency.
- Embedding cost.
- End-to-end event type macro-F1 khi dùng context từ embedding đó.

### Kết luận cần rút ra

Embedding nào phù hợp nhất cho báo tài chính tiếng Việt trong điều kiện chi phí và latency của project.

## Experiment 3: Pattern Library / Few-shot

### Mục tiêu

Đánh giá tác động của pattern examples.

### Cấu hình

| Run | Pattern count | Pattern selection |
| --- | --- | --- |
| E3.1 | 0 | none |
| E3.2 | 1 | most similar |
| E3.3 | 3 | diverse top patterns |
| E3.4 | 5 | diverse top patterns |
| E3.5 | 3 | include NO_EVENT pattern |

### Metrics

- Event detection F1.
- Event type macro-F1.
- JSON validity.
- False positive rate trên `NO_EVENT`.

### Kỳ vọng

3 pattern chất lượng thường tốt hơn 0-1 pattern. Quá nhiều pattern có thể làm model 8B nhiễu.

## Experiment 4: Model Comparison

### Mục tiêu

So sánh nhiều model hiện đại nhưng vẫn giữ workflow giống nhau.

### Cấu hình

| Run | Model |
| --- | --- |
| E4.1 | Qwen 2.5 7B/8B Instruct |
| E4.2 | Llama 3 8B Instruct |
| E4.3 | Mistral/Nemo 7B-12B nếu có |
| E4.4 | Teacher LLM mạnh làm upper bound |

### Metrics

- Event type macro-F1.
- JSON validity.
- Latency.
- Cost per article.

### Kết luận cần rút ra

Model nào phù hợp nhất cho demo local/chi phí thấp.

## Experiment 5: Label Representation

### Mục tiêu

Đáp ứng yêu cầu thử nghiệm cấu trúc nhãn đầu ra khác nhau.

### Cấu hình

| Run | Label schema | Output chính |
| --- | --- | --- |
| E5.1 | Flat event type | Chỉ dự đoán `event_type` |
| E5.2 | Hierarchical event type + subtype | Dự đoán `event_type` và `event_subtype` |
| E5.3 | Multi-label attributes | Dự đoán `event_attributes` vector 8 chiều |

### E5.1: Flat Event Type

Model chỉ chọn một nhãn chính trong taxonomy, ví dụ:

```json
{
  "event_type": "CONTRACT"
}
```

Ưu điểm: đơn giản, ổn định với dataset nhỏ, dễ báo cáo macro-F1 theo event type.

Nhược điểm: mất chi tiết như trúng thầu, hợp đồng mới, gia hạn hợp đồng.

### E5.2: Hierarchical Event Type + Subtype

Model chọn cả nhóm chính và subtype hợp lệ, ví dụ:

```json
{
  "event_type": "CONTRACT",
  "event_subtype": "BIDDING_WIN"
}
```

Quy tắc:

- `event_type` phải thuộc taxonomy chính.
- `event_subtype` phải thuộc danh sách subtype hợp lệ của `event_type`.
- Nếu không đủ bằng chứng chọn subtype, đặt `event_subtype=null`.

Ưu điểm: output giàu thông tin hơn, tốt cho phân tích lỗi và demo.

Nhược điểm: cần nhiều mẫu hơn cho từng subtype; có thể giảm accuracy nếu teacher labels nhiễu.

### E5.3: Multi-label Attribute Vector

Model dự đoán vector 8 chiều:

```json
{
  "event_attributes": {
    "financial": 1,
    "governance": 0,
    "legal": 0,
    "operation": 1,
    "market": 1,
    "strategic": 0,
    "capital_market": 0,
    "risk": 0
  }
}
```

Các chiều cố định:

- `financial`
- `governance`
- `legal`
- `operation`
- `market`
- `strategic`
- `capital_market`
- `risk`

Ưu điểm: biểu diễn được một sự kiện có nhiều khía cạnh cùng lúc.

Nhược điểm: đánh giá phức tạp hơn; cần Hamming loss, subset accuracy, micro/macro-F1.

### Metrics

- Flat schema: event type accuracy, macro-F1, per-class F1.
- Hierarchical schema: event type macro-F1, subtype accuracy, hierarchical exact match.
- Multi-label schema: micro-F1, macro-F1, Hamming loss, subset accuracy.

### Kết luận cần rút ra

Schema nào tạo output ổn định nhất với dữ liệu v1. Nếu subtype quá ít dữ liệu, flat schema có thể là lựa chọn production v1.

## Experiment 6: Feature Extraction / Rerank Variants

### Mục tiêu

Thử các cách rút trích đặc trưng/retrieval khác nhau theo tinh thần yêu cầu attention/pooling.

### Cấu hình

| Run | Feature strategy |
| --- | --- |
| E6.1 | Article-level embedding |
| E6.2 | Chunk-level embedding + max score |
| E6.3 | Chunk-level embedding + weighted score by event keywords |
| E6.4 | Optional attention pooling/reranker head |

### Metrics

- Retrieval Recall@K.
- Evidence accuracy.
- End-to-end F1.
- Latency.

### Ghi chú

Nếu không train module attention vì scope workflow thuần, vẫn có thể trình bày `E6.3` như rule-aware scoring. Nếu cần đáp ứng mạnh hơn phần deep learning, triển khai `E6.4` là module nhỏ, không phải fine-tune LLM.

## Experiment 7: Optional Lightweight Loss Function Study

### Mục tiêu

Giữ hướng workflow-first nhưng vẫn có phần thử loss functions nếu giảng viên yêu cầu rõ.

### Phạm vi

Không train toàn bộ LLM. Chỉ train một classifier/reranker nhỏ trên embedding để dự đoán:

- `HAS_EVENT` vs `NO_EVENT`, hoặc
- `event_type`, hoặc
- relevance của context retrieval.

### Cấu hình

| Run | Loss |
| --- | --- |
| E7.1 | Cross Entropy |
| E7.2 | Weighted Cross Entropy |
| E7.3 | Focal Loss |

### Metrics

- Macro-F1.
- Rare class recall.
- Training cost.
- Inference latency.

### Kết luận cần rút ra

Nếu dữ liệu lệch class, Weighted CE hoặc Focal Loss có thể cải thiện class hiếm như `LEGAL_RISK`, nhưng chỉ nên giữ nếu thật sự tăng metric.

## Experiment 8: Workflow Ablation

### Mục tiêu

Chứng minh từng thành phần workflow có giá trị.

### Cấu hình

| Run | Retrieval | Pattern | Validation | Repair |
| --- | --- | --- | --- | --- |
| E8.1 | Off | Off | Off | Off |
| E8.2 | On | Off | Off | Off |
| E8.3 | On | On | Off | Off |
| E8.4 | On | On | On | Off |
| E8.5 | On | On | On | On |

### Metrics

- Event F1.
- JSON validity.
- Hallucination rate.
- End-to-end latency.

## Experiment 9: Prompting and Grounding Strategy

### Mục tiêu

So sánh prompt sơ sài với prompt có chiến lược citation, grounded extraction và self-verification.

### Cấu hình

| Run | Prompt strategy |
| --- | --- |
| E9.1 | Direct extraction prompt |
| E9.2 | Schema-guided prompt |
| E9.3 | Grounded prompt: chỉ dùng article/context |
| E9.4 | Citation prompt: mọi event phải có evidence |
| E9.5 | Citation + self-verification |

### Metrics

- JSON validity.
- Evidence coverage.
- Hallucination rate.
- Unsupported field rate.
- Event type macro-F1.

### Kết luận cần rút ra

Grounded prompting và self-verification có giảm hallucination không, và có làm giảm recall quá nhiều không.

## Experiment 10: Fine-tune Optional Modules

### Mục tiêu

Chỉ fine-tune module nhỏ nếu cần, không fine-tune toàn bộ LLM 8B.

### Ứng viên module

| Module | Input | Output | Khi dùng |
| --- | --- | --- | --- |
| Event detector | embedding/article text | `HAS_EVENT`/`NO_EVENT` | Nếu false positive cao |
| Event type classifier | embedding/evidence chunk | `event_type` | Nếu LLM gán sai event type nhiều |
| Relevance reranker | query + candidate embedding/text | relevance score | Nếu retrieval top K nhiễu |

### Loss function

| Run | Loss |
| --- | --- |
| E10.1 | Cross Entropy |
| E10.2 | Weighted Cross Entropy |
| E10.3 | Focal Loss |

### Metrics

- Macro-F1.
- Rare class recall.
- Retrieval nDCG nếu train reranker.
- Inference latency.
- Training cost.

### Kết luận cần rút ra

Fine-tune module nhỏ có cải thiện điểm nghẽn cụ thể không. Nếu không cải thiện, giữ workflow không fine-tune.

## Experiment 11: Verification Ablation

### Mục tiêu

Đo riêng tác động của hallucination reduction.

### Cấu hình

| Run | Verification |
| --- | --- |
| E11.1 | No verification |
| E11.2 | JSON schema only |
| E11.3 | Schema + evidence exact match |
| E11.4 | Schema + evidence + argument grounding |
| E11.5 | Schema + evidence + self-verification |

### Metrics

- Post-verification hallucination rate.
- Evidence coverage.
- Dropped unsupported events.
- Event recall.
- JSON validity.

### Kết luận cần rút ra

Verification configuration nào giảm hallucination tốt nhất mà vẫn giữ được event recall chấp nhận được.

## Final Experiment Report

Báo cáo cuối nên có:

1. Dataset summary.
2. Bảng tất cả run.
3. Biểu đồ metric chính.
4. Error analysis.
5. Cấu hình tốt nhất.
6. Lý do chọn workflow-final cho demo.

## Cấu hình đề xuất để demo

Nếu không có kết quả bất thường, demo dùng:

```json
{
  "retrieval": "hybrid_vector_keyword_ticker",
  "chunking": "structure_aware_hierarchical",
  "retrieval_results_path": "data/retrieval/online_contexts.jsonl",
  "matched_patterns": "chunk_pattern_refs",
  "llm": "best_8b_on_dev_set",
  "label_schema": "flat_event_type",
  "validation": "schema_evidence_self_verification",
  "confidence_threshold": 0.60
}
```
