# 10. Writing Checklist

## Trước khi nộp báo cáo

### Nội dung bắt buộc

- Có giới thiệu bài toán.
- Có tính ứng dụng.
- Có contribution rõ ràng.
- Có mô tả dữ liệu.
- Có nguyên tắc gán nhãn.
- Có schema/taxonomy.
- Có kiến trúc hệ thống.
- Có thí nghiệm.
- Có metric định lượng.
- Có hạn chế.

### Contribution

Kiểm tra phần contribution có trả lời:

- Đề tài đóng góp gì?
- Vì sao đóng góp đó đáng giá?
- Khác gì baseline?
- Đo bằng metric nào?
- Có ví dụ minh họa không?

### Dữ liệu

Kiểm tra:

- ghi nguồn dữ liệu.
- ghi số lượng bài raw/clean.
- ghi cách clean/dedup.
- ghi phân bố event type.
- ghi rõ labels là AI-generated, không human review.

### Phương pháp

Kiểm tra:

- không gọi project là RAG app thuần.
- trình bày là evidence-grounded NLP pipeline.
- nêu rõ NLP tasks: event detection, classification, slot filling, grounding.
- giải thích vì sao không fine-tune toàn bộ LLM.

### Thí nghiệm

Kiểm tra có:

- baseline direct prompt.
- retrieval comparison.
- embedding comparison nếu chạy được.
- label representation comparison.
- verification ablation.
- error analysis.

### Ngôn ngữ trình bày

Tránh viết:

> Em dùng LLM để tạo bảng.

Nên viết:

> Hệ thống thực hiện structured information extraction từ văn bản tài chính tiếng Việt, trong đó LLM được điều khiển bởi schema, retrieval evidence và verification workflow.

## Checklist slide bảo vệ

Slide nên có:

1. Motivation.
2. Problem definition.
3. Dataset.
4. Event schema.
5. System architecture.
6. Key contributions.
7. Experiments.
8. Results.
9. Demo.
10. Limitations and future work.

## Những câu hỏi có thể bị hỏi

### “RAG có phải NLP không?”

Trả lời: RAG là module retrieval evidence. Bài toán chính vẫn là NLP structured information extraction gồm event detection, classification, slot filling và grounding.

### “Không human review nhãn thì metric có đáng tin không?”

Trả lời: Đây là AI-generated gold theo weak supervision. Metric đo mức khớp với nhãn teacher đã pass auto validation. Báo cáo ghi rõ hạn chế này và đề xuất human-in-the-loop ở future work.

### “Đề tài hơn prompt LLM trực tiếp ở đâu?”

Trả lời: Có schema, retrieval, chunk-attached pattern refs, verification và evaluation. Prompt trực tiếp thiếu evidence control và khó đo field-level metric.
