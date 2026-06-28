# 4. Related Work and Baselines

## Mục tiêu

Phần này giúp báo cáo trả lời: đề tài hơn gì so với các cách làm đơn giản hoặc giải pháp hiện có.

## Nhóm phương pháp liên quan

### 1. Rule-based extraction

Cách làm:

- dùng keyword như `trúng thầu`, `bổ nhiệm`, `phát hành`.
- viết regex để lấy số tiền/ngày tháng/tên công ty.

Ưu điểm:

- dễ giải thích.
- chạy nhanh.
- không cần huấn luyện hoặc vận hành LLM.

Nhược điểm:

- khó bao phủ nhiều cách diễn đạt tiếng Việt.
- dễ bỏ sót sự kiện viết gián tiếp.
- khó phân loại subtype phức tạp.
- khó trích xuất argument đa dạng.

FinEvent-VN hơn ở chỗ:

- dùng LLM cho hiểu ngữ nghĩa.
- dùng schema/verification để vẫn kiểm soát output.
- rule chỉ là tín hiệu hỗ trợ retrieval/rerank.

### 2. Traditional supervised NLP

Cách làm:

- train classifier cho event type.
- train sequence labeling/NER cho arguments.

Ưu điểm:

- đánh giá rõ.
- inference nhanh.
- ít hallucination hơn generative LLM.

Nhược điểm:

- cần dữ liệu gán nhãn thủ công lớn.
- khó mở rộng taxonomy nhanh.
- với dữ liệu ít dễ overfit.

FinEvent-VN hơn ở chỗ:

- dùng weak supervision bằng teacher LLM để tạo dataset ban đầu.
- không cần human review trong v1.
- dùng workflow để tận dụng model 8B mà vẫn có evidence.

### 3. Direct LLM prompting

Cách làm:

- đưa bài báo vào LLM.
- yêu cầu tạo bảng.

Ưu điểm:

- triển khai nhanh.
- baseline mạnh nếu dùng LLM lớn.

Nhược điểm:

- output không ổn định.
- dễ sai JSON.
- dễ hallucination.
- không có retrieval/pattern.
- khó biết field nào có bằng chứng.

FinEvent-VN hơn ở chỗ:

- có schema cố định.
- có pattern refs gắn với retrieved chunks.
- có retrieval evidence.
- có verification report.
- có evaluation/ablation.

### 4. Naive RAG

Cách làm:

- chunk cố định.
- embed.
- vector search.
- đưa top K vào prompt.

Nhược điểm:

- không tận dụng metadata tài chính.
- không có BM25 keyword signal.
- không có query rewriting.
- không rerank logic sự kiện.
- không đo retrieval quality.

FinEvent-VN hơn ở chỗ:

- structure-aware/hierarchical chunking.
- hybrid retrieval.
- metadata-aware retrieval.
- LLM reasoning rerank.
- retrieval metrics.

## Baseline cần chạy

| Baseline | Mục tiêu so sánh |
| --- | --- |
| Direct prompt zero-shot | LLM không retrieval/pattern |
| Schema-only prompt | Tác động của schema |
| Dense retrieval only | Tác động semantic search |
| BM25 only | Tác động keyword search |
| Hybrid retrieval | Tác động kết hợp lexical + semantic |
| Hybrid + context pattern refs | Tác động pattern refs gắn với retrieved chunks |
| Hybrid + verification | Tác động hallucination reduction |

## Cách trình bày kết quả

Không chỉ nói phương pháp mới tốt hơn. Cần có bảng metric:

- Event F1.
- Event type macro-F1.
- JSON validity.
- Hallucination rate.
- Retrieval Recall@K.
- Latency/cost.
