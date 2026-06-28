# 7. Methodology and System Design

## Mục tiêu

Trình bày phương pháp của đề tài dưới dạng kiến trúc hệ thống NLP có căn cứ bằng chứng.

## Kiến trúc tổng thể

```text
Raw financial articles
-> data cleaning and metadata extraction
-> structure-aware chunking
-> embedding/BM25/vector indexes
-> teacher labeling and chunk-attached pattern records
-> online query workflow
-> hybrid retrieval and reranking
-> LLM event extraction
-> verification and hallucination reduction
-> structured event table
```

## Thành phần 1: Data processing

Nhiệm vụ:

- crawl bài báo.
- parse title/body/date/source.
- normalize text.
- deduplicate.
- extract ticker/company hints.

Kết quả:

- clean corpus.
- metadata.
- PostgreSQL records.

## Thành phần 2: Event schema

Schema định nghĩa output chuẩn:

- document label.
- event type/subtype.
- event arguments.
- impact sentiment.
- evidence span.

Đây là cơ sở để:

- prompt LLM.
- validate output.
- đánh giá metric.
- lưu database.

## Thành phần 3: RAG preparation

Khác với naive RAG, project dùng:

- structure-aware chunking.
- hierarchical representation.
- multiple embedding models.
- pgvector.
- BM25.

## Thành phần 4: Retrieval and reranking

Retrieval gồm:

- query rewriting.
- query decomposition.
- BM25 search.
- dense vector search.
- metadata-aware hybrid scoring.
- rule-aware reranking.
- LLM reasoning reranking.

## Thành phần 5: Pattern library

Pattern library chứa cặp:

```text
evidence/article excerpt -> event JSON
```

Pattern giúp student LLM 8B:

- hiểu schema.
- bắt chước mức chi tiết.
- phân biệt `HAS_EVENT` và `NO_EVENT`.

## Thành phần 6: LLM extraction

Student LLM nhận:

- article.
- retrieved contexts.
- selected patterns.
- schema/taxonomy.
- grounded instruction.

Output là JSON theo schema.

## Thành phần 7: Verification

Verification kiểm tra:

- JSON validity.
- schema compliance.
- evidence span.
- argument grounding.
- taxonomy consistency.
- hallucination.

Unsupported fields bị loại hoặc set null.

## Vì sao workflow phù hợp hơn fine-tune toàn bộ LLM

Với dataset v1 nhỏ và nhãn tạo theo weak supervision, fine-tune toàn bộ LLM chưa phải lựa chọn ưu tiên:

- dễ overfit hoặc học theo pattern đã gặp.
- tốn tài nguyên so với quy mô dữ liệu.
- khó biết lỗi nằm ở bước nào trong pipeline.
- không tự giải quyết các lỗi ngoài mô hình như parse sai bài, retrieval sai context hoặc thiếu evidence.

Trong structured information extraction, output sai có thể đến từ nhiều nguồn:

- dữ liệu đầu vào bẩn.
- chunking làm mất câu chứa evidence.
- retrieval đưa nhầm bài liên quan về chủ đề nhưng không cùng sự kiện.
- prompt không ràng buộc schema đủ chặt.
- LLM sinh argument nghe hợp lý nhưng không có trong bài.

Workflow giúp:

- tách lỗi retrieval, extraction, verification.
- đánh giá từng module.
- sửa đúng điểm nghẽn.
- chỉ fine-tune module nhỏ nếu metric cho thấy module đó thật sự gây lỗi.
