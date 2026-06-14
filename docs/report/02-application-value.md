# 2. Tính Ứng Dụng

## Người dùng mục tiêu

Hệ thống có thể hỗ trợ:

- nhà đầu tư cá nhân cần theo dõi tin doanh nghiệp.
- chuyên viên phân tích tài chính.
- bộ phận quan hệ nhà đầu tư.
- hệ thống tin tức tài chính cần cấu trúc hóa dữ liệu.
- nhóm nghiên cứu NLP tiếng Việt trong miền tài chính.

## Giá trị thực tế

### 1. Giảm thời gian đọc tin

Thay vì đọc toàn bộ bài báo, người dùng nhận được bảng sự kiện ngắn gọn:

- công ty nào.
- sự kiện gì.
- chi tiết chính.
- bằng chứng nằm ở câu nào.

### 2. Chuẩn hóa dữ liệu phi cấu trúc

Tin báo thường ở dạng văn bản tự nhiên, khó đưa vào hệ thống phân tích. FinEvent-VN chuyển tin thành JSON/bảng, có thể lưu vào database hoặc xuất CSV.

### 3. Hỗ trợ theo dõi doanh nghiệp theo thời gian

Khi dữ liệu được cấu trúc hóa, có thể xây timeline:

- HPG ký hợp đồng.
- VHM mở bán dự án.
- PNJ thay đổi lãnh đạo.
- doanh nghiệp bị xử phạt.

### 4. Hỗ trợ phân tích định lượng sau này

Output sự kiện có thể kết hợp với:

- giá cổ phiếu.
- volume giao dịch.
- báo cáo tài chính.
- ngành nghề.

Project v1 không dự đoán giá, nhưng tạo nền dữ liệu cho các nghiên cứu sau.

### 5. Giảm hallucination so với hỏi LLM trực tiếp

Hệ thống bắt buộc mỗi event có evidence span, giúp người dùng kiểm tra được kết quả thay vì tin hoàn toàn vào output model.

## Kịch bản demo

### Kịch bản 1: Bài báo có sự kiện rõ

Input: bài báo “Công ty A trúng thầu dự án trị giá 500 tỷ”.

Output:

- ticker: A.
- event type: `CONTRACT`.
- subtype: `BIDDING_WIN`.
- arguments: contract value, project, partner.
- impact sentiment: `POSITIVE`.
- evidence span: câu chứa thông tin trúng thầu.

### Kịch bản 2: Bài phân tích chung

Input: bài nhận định thị trường hoặc bài bình luận giá cổ phiếu.

Output:

- `document_label=NO_EVENT`.
- `events=[]`.
- warning nếu bài không có hành động doanh nghiệp cụ thể.

### Kịch bản 3: Bài nhiều sự kiện

Input: bài vừa nói doanh nghiệp tăng vốn vừa mở rộng nhà máy.

Output:

- nhiều event records trong cùng một bài.
- mỗi event có evidence riêng.

## Giới hạn ứng dụng

Hệ thống không thay thế chuyên gia tài chính. Output chỉ là cấu trúc hóa thông tin trong bài báo, không phải lời khuyên đầu tư. Nếu bài báo sai, thiếu hoặc mang tính tin đồn, hệ thống chỉ có thể kiểm soát bằng evidence và confidence.

