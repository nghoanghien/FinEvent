# Academic Report Guide

Thư mục này dùng để chuẩn bị báo cáo học thuật cho đề tài FinEvent-VN. Nội dung ở đây không phải code workflow, mà là cách trình bày project thành một báo cáo có luận điểm, contribution, phương pháp, dữ liệu, thí nghiệm và hạn chế rõ ràng.

## Cấu trúc đề xuất cho báo cáo

| Chương | File | Vai trò |
| --- | --- | --- |
| 1 | [01-introduction.md](01-introduction.md) | Giới thiệu bài toán, bối cảnh và mục tiêu |
| 2 | [02-application-value.md](02-application-value.md) | Tính ứng dụng trong phân tích đầu tư và xử lý tin doanh nghiệp |
| 3 | [03-contributions.md](03-contributions.md) | Đóng góp chính của đề tài, phần quan trọng nhất |
| 4 | [04-related-work-and-baselines.md](04-related-work-and-baselines.md) | So sánh với phương pháp hiện tại và baseline |
| 5 | [05-dataset-description.md](05-dataset-description.md) | Dữ liệu thu thập, nguồn, thống kê sơ bộ |
| 6 | [06-labeling-methodology.md](06-labeling-methodology.md) | Nguyên tắc gán nhãn AI-generated gold và schema |
| 7 | [07-methodology-system-design.md](07-methodology-system-design.md) | Phương pháp, kiến trúc NLP-RAG, workflow |
| 8 | [08-experiments-and-evaluation.md](08-experiments-and-evaluation.md) | Thiết kế thí nghiệm, metrics, ablation |
| 9 | [09-limitations-and-future-work.md](09-limitations-and-future-work.md) | Hạn chế và hướng phát triển |
| 10 | [10-writing-checklist.md](10-writing-checklist.md) | Checklist trước khi nộp báo cáo |

## Luận điểm trung tâm

> FinEvent-VN xây dựng một hệ thống NLP trích xuất sự kiện doanh nghiệp từ báo tài chính tiếng Việt theo hướng evidence-grounded. Thay vì chỉ prompt LLM hoặc dùng RAG đơn giản, đề tài thiết kế schema sự kiện có cấu trúc, tạo dữ liệu mới bằng weak supervision, áp dụng retrieval/reranking có đánh giá, và kiểm định output bằng evidence để giảm hallucination.

Luận điểm cần nhấn mạnh trong báo cáo: đề tài tập trung vào **workflow để tăng độ chính xác và độ tin cậy của output**, không đặt nặng việc fine-tune lại toàn bộ mô hình. Với financial event extraction, kết quả tốt không chỉ là câu trả lời nghe hợp lý, mà phải đúng schema, đúng event type, có argument phù hợp và có evidence span trong bài báo.

Lý do không ưu tiên training end-to-end trong v1: dữ liệu ban đầu còn nhỏ, nhãn được tạo theo weak supervision, và lỗi của hệ thống có thể nằm ở nhiều bước khác nhau như parsing, retrieval, reranking, prompting hoặc verification. Nếu train toàn bộ chuỗi reasoning ngay từ đầu, mô hình dễ học theo các trường hợp đã gặp nhưng không giải quyết đúng điểm nghẽn. Vì vậy, project đo lỗi theo từng module trước, sau đó chỉ fine-tune module nhỏ nếu evaluation chứng minh module đó là nguyên nhân chính làm giảm độ chính xác.

Vì vậy, phần phương pháp nên trình bày LLM như một module trong pipeline:

```text
Clean data -> structured chunking -> hybrid retrieval -> reranking
-> pattern selection -> schema-guided extraction -> evidence verification
```

Thông điệp bảo vệ ngắn gọn:

> Với structured information extraction, training thêm chưa chắc hiệu quả nếu workflow chưa kiểm soát dữ liệu, context và evidence. Đề tài ưu tiên thiết kế workflow đo được lỗi, sửa đúng điểm nghẽn và giảm hallucination bằng evidence.

## Cách dùng thư mục này

- Dùng các file `01` đến `09` làm khung viết báo cáo.
- Dùng [03-contributions.md](03-contributions.md) làm phần trọng tâm cho contribution và slide bảo vệ.
- Khi có kết quả thật, điền số liệu vào các placeholder trong file dataset/evaluation.
- Không trình bày quá mức: nếu một module chỉ là optional hoặc chưa chạy, ghi là hướng mở rộng.
