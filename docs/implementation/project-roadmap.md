# Project Roadmap

## Mục tiêu

Chia project thành các milestone đủ nhỏ để có thể triển khai, test và báo cáo dần.

File này là roadmap tổng quan. Chi tiết input, output, công nghệ, metrics và done criteria của từng milestone nằm trong [milestone-implementation-details.md](milestone-implementation-details.md) và các file riêng trong [milestones/](milestones/).

## Milestone 0: Project Setup

Chi tiết: [m00-project-setup.md](milestones/m00-project-setup.md)

### Việc cần làm

- Tạo cấu trúc thư mục code.
- Tạo config cho API embedding/LLM.
- Tạo convention cho JSONL artifact.
- Tạo script chạy thử end-to-end với dữ liệu giả.

### Done khi

- Repo có cấu trúc rõ.
- Chạy được một script hello pipeline.
- Có file `.env.example` cho API keys nếu cần.

## Milestone 1: Data Collection

Chi tiết: [m01-data-ingestion.md](milestones/m01-data-ingestion.md)

### Việc cần làm

- Crawl 100-200 bài báo từ nguồn đã chọn.
- Parse title/date/body/source.
- Deduplicate và clean text.
- Tạo dictionary ticker-company cơ bản.

### Done khi

- Có `data/processed/articles_clean.jsonl`.
- Có báo cáo số lượng bài theo source/ticker.
- Có ít nhất 100 bài sạch.

## Milestone 2: Event Schema and Annotation

Chi tiết: [m02-schema-and-ai-labeling.md](milestones/m02-schema-and-ai-labeling.md)

### Việc cần làm

- Chốt schema trong [event-schema.md](../schema/event-schema.md).
- Dùng teacher LLM tạo nhãn theo schema.
- Auto validate JSON, enum, field bắt buộc và evidence span.
- Retry bằng AI repair nếu lỗi format/schema.
- Đánh dấu `HAS_EVENT`, `NO_EVENT`, event fields.

### Done khi

- Có `data/labels/events_gold.jsonl`.
- Có `data/labels/events_ai_generated.jsonl`.
- Có `data/labels/events_rejected.jsonl` nếu có output fail validation.
- Có ít nhất 6 event type xuất hiện.
- Có một phần dữ liệu `NO_EVENT`.

## Milestone 3: Embedding and Retrieval

Chi tiết: [m03-rag-preparation.md](milestones/m03-rag-preparation.md) và [m04-retrieval-reranking.md](milestones/m04-retrieval-reranking.md)

### Việc cần làm

- Chunk bài báo theo structure-aware/hierarchical strategy.
- Gọi Cloudflare embedding.
- So sánh thêm BGE-M3, multilingual E5, GTE multilingual nếu đủ thời gian.
- Lưu vector index mặc định bằng pgvector.
- Tạo FAISS baseline.
- Tạo BM25 index.
- Implement vector search, BM25, hybrid search, metadata-aware retrieval.
- Tạo retrieval logs.

### Done khi

- Query một bài mới trả top K context.
- Có metric Recall@K/Precision@K/MRR/nDCG trên dev set.
- Có ít nhất 4 cấu hình retrieval để so sánh.

## Milestone 4: Pattern Library

Chi tiết: [m05-pattern-library.md](milestones/m05-pattern-library.md)

### Việc cần làm

- Tạo pattern từ AI-generated gold labels.
- Embed pattern.
- Implement pattern selection top 3.
- Tạo prompt few-shot.

### Done khi

- Có `patterns_ai_generated.jsonl`.
- Extraction few-shot chạy được.
- Có so sánh zero-shot vs few-shot trên dev set.

## Milestone 5: LLM Extraction Pipeline

Chi tiết: [m06-online-extraction-workflow.md](milestones/m06-online-extraction-workflow.md) và [m07-verification-hallucination-reduction.md](milestones/m07-verification-hallucination-reduction.md)

### Việc cần làm

- Tạo LangGraph workflow online từ URL/text đến output.
- Tạo prompt template versioned.
- Gọi model 8B.
- Validate JSON output.
- Kiểm tra evidence grounding và hallucination.
- Implement repair khi JSON lỗi.
- Log raw output và validated output.

### Done khi

- Một bài báo đầu vào trả JSON đúng schema.
- Có xử lý `NO_EVENT`.
- JSON validity rate được đo.

## Milestone 6: Evaluation

Chi tiết: [m08-evaluation-ablation.md](milestones/m08-evaluation-ablation.md)

### Việc cần làm

- Viết script evaluate.
- Tính metric retrieval: Recall@K, Precision@K, MRR, nDCG.
- Tính metric extraction: event detection, event type, subtype, ticker, impact sentiment, slot-level F1.
- Tính metric output quality: JSON validity, evidence coverage, hallucination rate.
- Tạo bảng kết quả nhiều run.
- Làm error analysis.

### Done khi

- Có `reports/evaluation/eval_summary.md`.
- Có bảng so sánh ít nhất 3 cấu hình.
- Có kết luận cấu hình tốt nhất cho demo.

## Milestone 7: SE365 Experiments

Chi tiết: [experiment-plan.md](../experiments/experiment-plan.md)

### Việc cần làm

- Chạy model comparison.
- Chạy embedding model comparison.
- Chạy chunking strategy comparison.
- Chạy retrieval strategy comparison.
- Chạy reranking strategy comparison.
- Chạy prompting/grounding comparison.
- Chạy label representation comparison.
- Chạy pattern/few-shot ablation.
- Optional: lightweight classifier/reranker với CE/Weighted CE/Focal Loss nếu cần.

### Done khi

- Có bảng thí nghiệm trong `reports/evaluation/metrics_by_run.csv`.
- Có nhận xét định lượng cho từng thí nghiệm.
- Có hình/bảng dùng được cho báo cáo/slide.

## Milestone 8: Demo App

Chi tiết: [m09-demo-app.md](milestones/m09-demo-app.md)

### Việc cần làm

- Dựng Next.js frontend.
- Nhập URL/text.
- Hiển thị article preview.
- Hiển thị metadata hints.
- Hiển thị retrieval contexts.
- Hiển thị patterns.
- Hiển thị bảng sự kiện và evidence.
- Hiển thị verification report và diagnostics.

### Done khi

- Chạy được frontend local và gọi FastAPI backend.
- Demo được 1 bài `HAS_EVENT` và 1 bài `NO_EVENT`.
- Output có thể export JSON/CSV.

## Milestone 9: Final Report and Slides

Chi tiết: [m10-final-report-slides.md](milestones/m10-final-report-slides.md) và [../report/README.md](../report/README.md)

### Việc cần làm

- Viết báo cáo theo cấu trúc học thuật.
- Chuyển metric thành bảng/biểu đồ.
- Chuẩn bị demo script.
- Chuẩn bị phần hạn chế và hướng phát triển.

### Done khi

- Báo cáo giải thích rõ workflow, dữ liệu, thí nghiệm, metrics.
- Slide có kiến trúc, schema, kết quả, demo.
- Có thể tái chạy demo trước buổi bảo vệ.

## Cấu trúc code đề xuất

```text
fin-event-vn/
  app/
  configs/
  data/
  docs/
  reports/
  runs/
  src/
    crawler/
    data_processing/
    chunking/
    embeddings/
    retrieval/
    reranking/
    patterns/
    extraction/
    validation/
    workflows/
    evaluation/
  tests/
```

## Thứ tự ưu tiên thực tế

Nếu thời gian hạn chế:

1. Làm data + schema thật chắc.
2. Làm extraction prompt + validation.
3. Làm RAG preparation: chunking, embedding, pgvector, BM25.
4. Làm retrieval/rerank.
5. Làm evaluation.
6. Làm demo app.
7. Chạy thêm thí nghiệm để tăng điểm.

Không nên bắt đầu bằng fine-tuning khi chưa có AI-generated gold labels và evaluation script.

## Definition of Done toàn project

Project hoàn thành khi có:

- Dataset mới tiếng Việt.
- Schema sự kiện rõ ràng.
- Pipeline chạy end-to-end.
- Evaluation định lượng.
- Ít nhất 3 nhóm thí nghiệm.
- Demo app.
- Báo cáo giải thích được vì sao RAG là tầng evidence grounding, còn project cốt lõi vẫn là NLP event extraction.
