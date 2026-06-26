# Admin Dashboard Documentation

## Tài liệu mới liên quan workflow graph

- [13-milestone-graph-composer.md](13-milestone-graph-composer.md): React Flow composer graph M00-M08, backend catalog hydration, dependency, toggle downstream, drawer/modal config và confirm run.

Thư mục này mô tả thiết kế UI admin cho FinEvent-VN. Mục tiêu của dashboard là
giúp theo dõi, chạy, debug và trình diễn toàn bộ pipeline M00-M08 một cách trực
quan, thay vì chỉ xem terminal hoặc mở từng file artifact thủ công.

Dashboard này khác với demo app người dùng cuối. Demo app tập trung vào việc nhập
một bài báo và xem bảng sự kiện. Admin dashboard tập trung vào vận hành hệ thống:
chạy milestone, xem live logs, xem DB, xem report, xem output có cấu trúc và phân
tích lỗi.

## Thứ Tự Đọc Nhanh

1. [Product Scope](01-product-scope.md) - mục tiêu, audience, use case.
2. [Information Architecture](02-information-architecture.md) - cấu trúc màn hình.
3. [Workflow Runner](03-workflow-runner.md) - nút chạy milestone/workflow.
4. [Live Logs And Observability](04-live-logs-observability.md) - log realtime như Colab.
5. [Database Browser](05-database-browser.md) - xem dữ liệu trong PostgreSQL.
6. [Report Viewer](06-report-viewer.md) - xem Markdown/CSV/JSONL report.
7. [Structured Output Viewer](07-structured-output-viewer.md) - xem output model dạng bảng.
8. [API Contract](08-api-contract.md) - API FastAPI cần có.
9. [Backend Job Design](09-backend-job-design.md) - job runner và lưu trạng thái run.
10. [Frontend Implementation Plan](10-frontend-implementation-plan.md) - kế hoạch Next.js.
11. [Testing And Acceptance](11-testing-acceptance.md) - test cases và done criteria.
12. [Report Charts Visualization](12-report-charts-visualization.md) - biểu đồ hóa report.
13. [Milestone Graph Composer](13-milestone-graph-composer.md) - React Flow graph chọn node M00-M08, dependency, drawer/modal config và confirm run.

## Mục Tiêu Chính

- Có một nơi duy nhất để quan sát pipeline đang chạy.
- Bấm chạy từng milestone hoặc workflow lớn mà không cần nhớ CLI.
- Xem từng dòng log realtime giống Google Colab.
- Xem bài báo, labels, chunks, embeddings metadata, patterns và extraction runs trong DB.
- Xem tất cả report sau khi chạy xong bằng giao diện trực quan.
- Xem output model dạng bảng, không chỉ xem JSON thô.
- Hỗ trợ debug lỗi nhanh: lỗi ở bước nào, command nào, artifact nào, report nào.

## Phạm Vi V1

V1 là admin nội bộ cho một người dùng, ưu tiên chạy được và debug tốt:

- Chưa cần authentication phức tạp.
- Chưa cần multi-user job scheduling.
- Chưa cần deploy production.
- Chưa cần edit dữ liệu trực tiếp trong DB, trừ ticker dictionary nếu đã có API.
- Chưa cần thay thế CLI; UI sẽ gọi backend, backend gọi lại các CLI/workflow hiện có.

## Tech Stack Đề Xuất

| Layer | Công nghệ | Vai trò |
| --- | --- | --- |
| Frontend | Next.js + TypeScript | UI admin, routing, table, report viewer |
| UI library | Tailwind CSS + shadcn/ui | Giao diện dashboard nhất quán, làm nhanh |
| Data fetching | TanStack Query | Cache API, refetch trạng thái run, retry |
| Realtime logs | Server-Sent Events | Stream log từng dòng từ backend đến browser |
| Backend API | FastAPI | Expose workflow/job/report/DB APIs |
| Job runner v1 | Python subprocess | Gọi CLI hiện có như `finevent.ingestion`, `finevent.rag` |
| Runtime DB | PostgreSQL + pgvector | Lưu metadata, run state, traces, dictionary |
| Artifacts | `data/`, `reports/`, `runs/` | File output và report đã sinh bởi pipeline |

## Các Màn Hình Chính

| Màn hình | Mục đích |
| --- | --- |
| Overview | Tình trạng DB, artifact, metrics mới nhất, run gần nhất |
| Workflow Runner | Chạy từng milestone hoặc workflow lớn |
| Run Detail | Timeline step, live logs, artifacts, errors |
| Database Browser | Xem articles, chunks, labels, patterns, extraction runs |
| Reports | Render Markdown/CSV/JSONL report |
| Outputs | Xem prediction/event table, evidence, verification |
| Settings & Health | Kiểm tra `.env`, API, PostgreSQL, pgvector, model endpoints |

## Liên Quan Với Milestone

Dashboard này nên được xem là milestone mới:

- **M09 Admin Dashboard & Observability**: vận hành, theo dõi, debug pipeline.
- Demo app người dùng cuối có thể là M10 hoặc giữ ở `m09-demo-app.md` như demo riêng.
- M10/M11 về báo cáo/slides có thể dùng chính dashboard này để demo trước hội đồng.
