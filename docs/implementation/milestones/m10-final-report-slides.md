# M10: Final Report and Slides

## Mục tiêu

Hoàn thiện báo cáo học thuật, slide bảo vệ và demo script. Milestone này biến toàn bộ artifact kỹ thuật thành câu chuyện nghiên cứu rõ ràng.

## Input

```text
docs/report/
reports/evaluation/
reports/data/
app demo
```

## Output

```text
reports/final/final_report.md hoặc .docx
reports/final/slides_outline.md
reports/final/demo_script.md
reports/final/figures/
```

## Công nghệ

- Markdown làm bản thảo.
- Word/Google Docs nếu cần nộp.
- PowerPoint/Google Slides nếu cần trình bày.
- matplotlib/seaborn cho biểu đồ.

## Cách triển khai chi tiết

### Bước 1: Chốt thesis statement

Luận điểm chính:

> FinEvent-VN là một evidence-grounded NLP pipeline trích xuất sự kiện doanh nghiệp từ báo tài chính tiếng Việt, kết hợp dữ liệu mới, event schema có cấu trúc, advanced retrieval, LLM extraction và verification để giảm hallucination.

### Bước 2: Viết báo cáo theo cụm

Dựa trên `docs/report/`:

- giới thiệu đề tài.
- tính ứng dụng.
- contribution.
- dữ liệu.
- gán nhãn.
- phương pháp.
- thí nghiệm.
- kết quả.
- hạn chế.

### Bước 3: Chuẩn bị bảng/biểu đồ

Cần có:

- dataset summary.
- label distribution.
- retrieval metric table.
- extraction metric table.
- ablation table.
- error analysis.

### Bước 4: Chuẩn bị slide

Slide nên có:

1. Problem.
2. Motivation.
3. Dataset.
4. Event schema.
5. Method architecture.
6. Contributions.
7. Experiments.
8. Results.
9. Demo.
10. Limitations and future work.

### Bước 5: Demo script

Chuẩn bị:

- 1 bài `HAS_EVENT`.
- 1 bài `NO_EVENT`.
- 1 bài có nhiều event nếu có.
- backup screenshots nếu app/model lỗi.

## Kiểm thử

- Chạy demo trước buổi bảo vệ.
- Kiểm tra bảng metric khớp file evaluation.
- Kiểm tra báo cáo không nói quá khả năng project.
- Kiểm tra mọi contribution đều có evidence trong implementation/evaluation.

## Done Criteria

- Có bản báo cáo hoàn chỉnh.
- Có slide.
- Có demo script.
- Có figures/tables dùng trong báo cáo.
- Có phần contribution rõ, sâu và bảo vệ được.

