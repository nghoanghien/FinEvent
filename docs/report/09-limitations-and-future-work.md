# 9. Limitations and Future Work

## Hạn chế

### 1. AI-generated gold labels

Nhãn do teacher LLM sinh, không có human review. Vì vậy có thể có label noise.

Cách trình bày:

> Đây là ground truth vận hành cho project v1 theo hướng weak supervision, không phải nhãn chuyên gia tài chính.

### 2. Dataset v1 còn nhỏ

Tập dữ liệu ban đầu khoảng 100-200 bài có thể chưa bao phủ đầy đủ mọi event type/subtype.

### 3. Source coverage giới hạn

Project v1 ưu tiên báo tài chính công khai, chưa xử lý mạng xã hội hoặc diễn đàn có nhiễu cao.

### 4. Ticker mapping có thể chưa hoàn chỉnh

Một số bài chỉ nêu tên doanh nghiệp, không nêu mã cổ phiếu.

### 5. LLM reasoning rerank tốn chi phí

LLM rerank giúp lọc tốt hơn nhưng tăng latency/token cost.

### 6. Không dự đoán tác động giá

Project chỉ trích xuất sự kiện và chiều hướng tác động trong văn bản, không dự đoán giá cổ phiếu hoặc khuyến nghị đầu tư.

## Hướng phát triển

### 1. Human-in-the-loop validation

Thêm một tập nhỏ được chuyên gia/nhóm người kiểm tra để ước lượng chất lượng AI-generated labels.

### 2. Fine-tune embedding domain-specific

Train embedding bằng contrastive learning trên cặp bài cùng/khác event type.

### 3. Fine-tune reranker

Huấn luyện reranker nhỏ để thay thế LLM reasoning rerank khi cần giảm chi phí.

### 4. Mở rộng nguồn dữ liệu

Thêm:

- thông báo doanh nghiệp.
- báo cáo quan hệ nhà đầu tư.
- diễn đàn tài chính.
- mạng xã hội nếu có chiến lược lọc nhiễu.

### 5. Liên kết với dữ liệu thị trường

Kết hợp event timeline với:

- giá cổ phiếu.
- volume.
- ngành.
- báo cáo tài chính.

### 6. Public Vietnamese RAG/Event Extraction Benchmark

Nếu dataset được mở rộng và kiểm tra kỹ hơn, có thể đóng góp benchmark tiếng Việt cho financial event extraction.

