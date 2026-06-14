# Milestones Overview

Thư mục này tách riêng từng milestone triển khai để khi code có thể mở đúng file cần làm, không phải đọc một tài liệu dài.

## Thứ tự triển khai đề xuất

| Milestone | File | Vai trò |
| --- | --- | --- |
| M0 | [m00-project-setup.md](m00-project-setup.md) | Tạo nền repo, config, logging, test skeleton |
| M1 | [m01-data-ingestion.md](m01-data-ingestion.md) | Crawl, parse, clean và lưu bài báo |
| M2 | [m02-schema-and-ai-labeling.md](m02-schema-and-ai-labeling.md) | Gán nhãn AI-generated gold theo schema |
| M3 | [m03-rag-preparation.md](m03-rag-preparation.md) | Chunking, embedding, ChromaDB, FAISS, BM25 |
| M4 | [m04-retrieval-reranking.md](m04-retrieval-reranking.md) | Hybrid retrieval, metadata-aware retrieval, reranking |
| M5 | [m05-pattern-library.md](m05-pattern-library.md) | Tạo và truy hồi pattern/few-shot examples |
| M6 | [m06-online-extraction-workflow.md](m06-online-extraction-workflow.md) | LangGraph workflow từ URL/text đến event JSON |
| M7 | [m07-verification-hallucination-reduction.md](m07-verification-hallucination-reduction.md) | Evidence verification và giảm hallucination |
| M8 | [m08-evaluation-ablation.md](m08-evaluation-ablation.md) | Evaluation scripts, metrics, ablation study |
| M9 | [m09-demo-app.md](m09-demo-app.md) | Streamlit demo app |
| M10 | [m10-final-report-slides.md](m10-final-report-slides.md) | Hoàn thiện báo cáo, slide và demo script |

## Quy tắc triển khai

- Mỗi milestone phải tạo artifact có thể kiểm tra được.
- Không viết logic chỉ chạy trong app; core logic phải nằm ở `src/` để test được.
- Mọi model/prompt/retrieval config phải có version.
- Mọi output từ LLM phải được log raw và validated output.
- Không fine-tune module nào trước khi có evaluation script để đo tác động.

