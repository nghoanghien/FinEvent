# 01 - Product Scope

## Mục Tiêu

Admin Dashboard giúp người phát triển project FinEvent-VN vận hành pipeline
trích xuất sự kiện tài chính một cách trực quan:

- chạy từng milestone hoặc toàn bộ pipeline;
- theo dõi log realtime;
- xem trạng thái DB và artifact;
- xem output model có cấu trúc;
- xem report/metrics sau khi chạy;
- debug lỗi nhanh hơn so với terminal.

Dashboard không thay thế core pipeline. Core NLP, retrieval, labeling, extraction
và evaluation vẫn nằm ở backend Python. UI chỉ điều phối, hiển thị và gọi API.

## Người Dùng Chính

| Người dùng | Nhu cầu |
| --- | --- |
| Người phát triển project | Chạy pipeline, debug lỗi, xem artifact, so sánh run |
| Người viết báo cáo | Mở nhanh report, metrics, error examples |
| Người demo đồ án | Trình diễn workflow đang chạy và output có evidence |
| Giảng viên/người xem demo | Xem hệ thống có pipeline, logs, metrics, output rõ ràng |

## Vấn Đề Hiện Tại

Khi chỉ chạy CLI:

- khó biết pipeline đang chạy đến bước nào;
- output chỉ hiện trong terminal, không tiện xem lại;
- log dài khó đọc;
- report nằm rải rác trong `reports/`;
- output JSON khó xem với người không code;
- DB có dữ liệu nhưng không có giao diện quan sát;
- khi lỗi phải mở nhiều file để truy ra nguyên nhân.

## Use Cases Bắt Buộc

### UC1 - Chạy từng milestone

Người dùng chọn một milestone như M01, M03, M06 hoặc M08 và bấm chạy.
Dashboard tạo một run mới, stream log và hiển thị artifact sau khi hoàn tất.

### UC2 - Chạy workflow lớn

Người dùng chọn workflow:

- Data + embedding preparation;
- Teacher labeling;
- Student 8B extraction;
- Full M00-M08;
- Evaluation/report generation.

Dashboard chạy nhiều step liên tiếp và hiển thị timeline.

### UC3 - Xem live logs giống Colab

Trong lúc chạy, UI hiển thị log từng dòng:

- timestamp;
- step;
- level;
- message;
- stdout/stderr;
- progress counters nếu có.

### UC4 - Xem dữ liệu trong DB

Người dùng mở Database Browser để xem:

- bài báo đã ingest;
- metadata/ticker hints;
- chunks;
- gold labels;
- patterns;
- extraction runs;
- node traces.

### UC5 - Xem output model dạng bảng

Prediction JSON được hiển thị thành:

- bảng event;
- bảng event arguments;
- evidence span;
- validation issues;
- verification report;
- raw JSON khi cần debug.

### UC6 - Xem report trực quan

Người dùng mở report viewer để xem:

- Markdown report;
- CSV metrics dưới dạng table;
- JSONL error examples dưới dạng list/detail.

## Ngoài Phạm Vi V1

- Quản lý user/role phức tạp.
- Chỉnh sửa trực tiếp gold labels bằng UI.
- Training/fine-tuning qua UI.
- Deploy public internet.
- Multi-worker distributed job scheduling.
- Notebook replacement hoàn chỉnh.

## Thành Công Được Đo Như Thế Nào

V1 được xem là thành công nếu:

- chạy được ít nhất một workflow từ UI;
- xem được live logs trong browser;
- xem được report sau khi run xong;
- xem được articles và extraction runs từ DB;
- output model hiển thị thành bảng;
- lỗi workflow hiện rõ ở step tương ứng;
- không cần mở terminal để biết pipeline đang làm gì.

