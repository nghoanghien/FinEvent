# FinEvent-VN Documentation

## Tài liệu mới

- [Backend Milestone Graph Runner API](backend-api/05-milestone-graph-runner.md)
- [Admin Milestone Graph Composer](admin-dashboard/13-milestone-graph-composer.md)

FinEvent-VN là project trích xuất sự kiện tài chính doanh nghiệp từ báo tài chính tiếng Việt. Hướng chính của project là **evidence-grounded NLP pipeline**: dùng retrieval/RAG như tầng truy xuất bằng chứng, còn lõi NLP là phát hiện sự kiện, phân loại taxonomy, slot filling, kiểm định evidence và đánh giá định lượng.

Tài liệu được chia nhỏ để dễ đọc, dễ code và dễ chuyển thành báo cáo SE365.

## Cấu trúc thư mục

```text
docs/
  README.md
  overview/
    project-overview.md
    rag-nlp-positioning.md
    technology-stack.md
  adr/
    README.md
    0001-database-layer-strategy.md
  backend-api/
    README.md
    01-overview.md
    ...
    05-milestone-graph-runner.md
  admin-dashboard/
    README.md
    01-product-scope.md
    ...
    13-milestone-graph-composer.md
  schema/
    event-schema.md
  workflows/
    data/
      data-workflow.md
      rag-preparation-workflow.md
    retrieval/
      embedding-retrieval-workflow.md
    patterns/
      pattern-library-workflow.md
    extraction/
      article-query-extraction-workflow.md
      llm-extraction-workflow.md
      verification-hallucination-workflow.md
    evaluation/
      evaluation-workflow.md
    demo/
      demo-app-workflow.md
  experiments/
    experiment-plan.md
  implementation/
    project-roadmap.md
    milestone-implementation-details.md
    milestones/
      m00-project-setup.md
      ...
      m10-final-report-slides.md
  report/
    README.md
    01-introduction.md
    02-application-value.md
    03-contributions.md
    ...
  runbooks/
    local-stack.md
```

## Cách đọc nhanh

1. Đọc [Project Overview](overview/project-overview.md) để nắm bài toán, kiến trúc và phạm vi.
2. Đọc [RAG and NLP Positioning](overview/rag-nlp-positioning.md) để hiểu cách trình bày RAG trong nhóm NLP.
3. Đọc [Technology Stack](overview/technology-stack.md) để chốt DB, vector store, workflow framework và model runtime.
4. Đọc [Architecture Decision Records](adr/README.md) khi cần hiểu các quyết định kiến trúc dài hạn.
5. Đọc [Event Schema](schema/event-schema.md) trước khi code extraction, vì mọi module đều phải dùng chung schema này.
6. Đọc các workflow theo đúng luồng: data -> RAG preparation -> retrieval -> pattern -> extraction -> verification -> evaluation -> demo.
7. Đọc [Experiment Plan](experiments/experiment-plan.md) để biết cần chạy thí nghiệm nào cho SE365.
8. Đọc [Project Roadmap](implementation/project-roadmap.md), [Milestone Implementation Details](implementation/milestone-implementation-details.md) và từng file trong [implementation/milestones/](implementation/milestones/) để quản lý tiến độ code.
9. Đọc [Admin Dashboard Documentation](admin-dashboard/README.md) khi cần thiết kế UI chạy workflow, xem live logs, DB, reports và structured outputs.
10. Đọc [Academic Report Guide](report/README.md), đặc biệt [Contributions](report/03-contributions.md), để viết báo cáo nộp môn.
11. Đọc [Local Stack Runbook](runbooks/local-stack.md) để chạy DB, backend và frontend bằng Docker Compose.

## Tài liệu theo nhóm

### Overview

| File | Vai trò |
| --- | --- |
| [project-overview.md](overview/project-overview.md) | Tổng quan đề tài, mục tiêu, phạm vi, kiến trúc hệ thống |
| [rag-nlp-positioning.md](overview/rag-nlp-positioning.md) | Định vị RAG trong đề tài NLP, tránh bị xem là naive RAG |
| [technology-stack.md](overview/technology-stack.md) | Long-term tech stack, DB, vector search, workflow runtime, backend, model serving |

### Architecture Decision Records

| File | Vai trò |
| --- | --- |
| [README.md](adr/README.md) | Index các quyết định kiến trúc |
| [0001-database-layer-strategy.md](adr/0001-database-layer-strategy.md) | Chiến lược database layer: Raw SQL, SQLAlchemy Core, Alembic và ORM có chọn lọc |

### Backend API

| File | Vai trò |
| --- | --- |
| [README.md](backend-api/README.md) | Index tài liệu FastAPI admin backend |
| [05-milestone-graph-runner.md](backend-api/05-milestone-graph-runner.md) | API, registry package, edge labels và command mapping cho workflow graph M00-M08 |

### Admin Dashboard

| File | Vai trò |
| --- | --- |
| [README.md](admin-dashboard/README.md) | Index bộ tài liệu UI admin và observability |
| [01-product-scope.md](admin-dashboard/01-product-scope.md) | Mục tiêu, audience, use cases và phạm vi v1 |
| [02-information-architecture.md](admin-dashboard/02-information-architecture.md) | Cấu trúc màn hình và luồng điều hướng |
| [03-workflow-runner.md](admin-dashboard/03-workflow-runner.md) | Thiết kế nút chạy từng milestone/workflow |
| [04-live-logs-observability.md](admin-dashboard/04-live-logs-observability.md) | Live logs giống Colab, timeline và progress |
| [05-database-browser.md](admin-dashboard/05-database-browser.md) | UI xem articles, chunks, labels, patterns, extraction runs trong DB |
| [06-report-viewer.md](admin-dashboard/06-report-viewer.md) | UI xem Markdown/CSV/JSONL reports |
| [07-structured-output-viewer.md](admin-dashboard/07-structured-output-viewer.md) | UI xem event table, evidence, arguments, verification |
| [08-api-contract.md](admin-dashboard/08-api-contract.md) | API FastAPI cần có cho admin dashboard |
| [09-backend-job-design.md](admin-dashboard/09-backend-job-design.md) | Thiết kế job runner, run state và log persistence |
| [10-frontend-implementation-plan.md](admin-dashboard/10-frontend-implementation-plan.md) | Kế hoạch triển khai Next.js frontend |
| [11-testing-acceptance.md](admin-dashboard/11-testing-acceptance.md) | Test cases và done criteria |
| [12-report-charts-visualization.md](admin-dashboard/12-report-charts-visualization.md) | Report charts, visualization và chart artifacts |
| [13-milestone-graph-composer.md](admin-dashboard/13-milestone-graph-composer.md) | React Flow composer graph M00-M08, dependency, drawer/modal config và confirm run |

### Schema

| File | Vai trò |
| --- | --- |
| [event-schema.md](schema/event-schema.md) | Schema bảng sự kiện, taxonomy nhãn, subtype, multi-label vector, argument rules |

### Workflows

| File | Vai trò |
| --- | --- |
| [data-workflow.md](workflows/data/data-workflow.md) | Thu thập, làm sạch, gán nhãn và version dữ liệu |
| [rag-preparation-workflow.md](workflows/data/rag-preparation-workflow.md) | Workflow offline chuẩn bị corpus, chunking, embedding, index |
| [embedding-retrieval-workflow.md](workflows/retrieval/embedding-retrieval-workflow.md) | Embedding, BM25, vector search, metadata-aware retrieval, reranking |
| [pattern-library-workflow.md](workflows/patterns/pattern-library-workflow.md) | Tạo thư viện pattern/gold examples bằng teacher LLM và auto validation |
| [article-query-extraction-workflow.md](workflows/extraction/article-query-extraction-workflow.md) | Workflow online từ URL/text đến bảng sự kiện |
| [llm-extraction-workflow.md](workflows/extraction/llm-extraction-workflow.md) | Workflow dùng LLM 8B để sinh bảng sự kiện có cấu trúc |
| [verification-hallucination-workflow.md](workflows/extraction/verification-hallucination-workflow.md) | Verification, citation, groundedness và hallucination reduction |
| [evaluation-workflow.md](workflows/evaluation/evaluation-workflow.md) | Đánh giá từng flow và end-to-end |
| [demo-app-workflow.md](workflows/demo/demo-app-workflow.md) | Thiết kế app demo cơ bản |

### Experiments

| File | Vai trò |
| --- | --- |
| [experiment-plan.md](experiments/experiment-plan.md) | Kế hoạch thí nghiệm đáp ứng SE365 |

### Implementation

| File | Vai trò |
| --- | --- |
| [project-roadmap.md](implementation/project-roadmap.md) | Lộ trình triển khai project |
| [milestone-implementation-details.md](implementation/milestone-implementation-details.md) | Index các milestone chi tiết |
| [milestones/](implementation/milestones/) | Mỗi milestone là một file riêng, có cách làm, công nghệ, kiểm thử, metrics |

### Academic Report

| File | Vai trò |
| --- | --- |
| [README.md](report/README.md) | Mục lục và luận điểm trung tâm cho báo cáo |
| [01-introduction.md](report/01-introduction.md) | Giới thiệu đề tài |
| [02-application-value.md](report/02-application-value.md) | Tính ứng dụng |
| [03-contributions.md](report/03-contributions.md) | Đóng góp chính của đề tài |
| [04-related-work-and-baselines.md](report/04-related-work-and-baselines.md) | So sánh baseline và phương pháp liên quan |
| [05-dataset-description.md](report/05-dataset-description.md) | Mô tả dữ liệu thu thập |
| [06-labeling-methodology.md](report/06-labeling-methodology.md) | Nguyên tắc gán nhãn dữ liệu |
| [07-methodology-system-design.md](report/07-methodology-system-design.md) | Phương pháp và kiến trúc hệ thống |
| [08-experiments-and-evaluation.md](report/08-experiments-and-evaluation.md) | Thí nghiệm và đánh giá |
| [09-limitations-and-future-work.md](report/09-limitations-and-future-work.md) | Hạn chế và hướng phát triển |
| [10-writing-checklist.md](report/10-writing-checklist.md) | Checklist viết báo cáo và bảo vệ |

## Nguyên tắc chung

- Mọi output máy học phải có dữ liệu nguồn và evidence đi kèm.
- LLM không được tự suy diễn thông tin không có trong bài báo.
- RAG không phải mục tiêu cuối; RAG là module retrieval/evidence grounding cho bài toán NLP trích xuất sự kiện.
- Nếu không đủ bằng chứng, hệ thống phải trả `NO_EVENT` hoặc confidence thấp, không ép sinh sự kiện.
- Các thí nghiệm phải đo bằng metric định lượng, không chỉ mô tả cảm tính.
- Dataset, prompt, model config và kết quả đánh giá phải được version để có thể tái lập.

## Artifact chính

| Artifact | Ví dụ đường dẫn đề xuất | Mô tả |
| --- | --- | --- |
| Raw articles | `data/raw/articles.jsonl` | Bài báo crawl nguyên bản |
| Clean articles | `data/processed/articles_clean.jsonl` | Bài báo đã chuẩn hóa |
| AI-generated gold labels | `data/labels/events_gold.jsonl` | Nhãn do teacher LLM sinh và được chấp nhận làm ground truth vận hành sau auto validation |
| Primary DB | PostgreSQL + pgvector | Metadata, chunks, labels, embeddings, run logs |
| FAISS baseline | `data/vector_store/faiss/` | Baseline vector search cho ablation |
| Pattern library | `data/patterns/patterns.jsonl` | Few-shot examples chất lượng cao |
| Extraction logs | `runs/extraction/` | Log từng bước workflow |
| Evaluation reports | `reports/evaluation/` | Bảng metric, error analysis |
