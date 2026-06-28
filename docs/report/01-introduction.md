# 1. Giới Thiệu Đề Tài

## Bối cảnh

Báo cáo tài chính doanh nghiệp thường được công bố theo quý hoặc theo năm, vì vậy thông tin chính thức có độ trễ. Trong khi đó, báo tài chính, cổng thông tin doanh nghiệp và các nguồn tin công khai lại cập nhật hằng ngày các sự kiện có thể ảnh hưởng đến triển vọng kinh doanh của doanh nghiệp.

Các sự kiện này có thể gồm:

- ký hợp đồng lớn hoặc trúng thầu.
- tăng vốn, phát hành cổ phiếu/trái phiếu.
- M&A, thoái vốn, chuyển nhượng tài sản.
- thay đổi lãnh đạo.
- mở rộng nhà máy, dự án, thị trường.
- bị điều tra, kiện tụng, xử phạt.
- công bố hợp tác chiến lược hoặc được cấp phép dự án.

Các chuyên gia tài chính có thể đọc tin và nhanh chóng nhận ra sự kiện quan trọng, nhưng việc xử lý thủ công nhiều nguồn tin mỗi ngày tốn thời gian và khó mở rộng.

## Bài toán

Đề tài đặt ra bài toán:

> Từ một bài báo tài chính tiếng Việt phi cấu trúc, hệ thống tự động phát hiện và trích xuất các sự kiện doanh nghiệp thành bảng dữ liệu có cấu trúc, kèm bằng chứng trong văn bản.

Output mong muốn không phải là câu trả lời tự do, mà là bản ghi sự kiện:

- doanh nghiệp/mã cổ phiếu.
- loại sự kiện và subtype.
- các argument quan trọng.
- chiều hướng tác động.
- evidence span.
- confidence.

## Luận điểm phương pháp

Đề tài không đặt trọng tâm vào việc huấn luyện lại toàn bộ mô hình để ép mô hình học toàn bộ chuỗi suy luận end-to-end. Thay vào đó, đề tài tập trung vào cách kết hợp **NLP, retrieval và workflow kiểm định** để đưa ra kết quả chính xác và có thể kiểm soát hơn. Trong bài toán trích xuất thông tin có cấu trúc, lỗi thường không chỉ đến từ năng lực của mô hình nền, mà còn đến từ dữ liệu đầu vào, context retrieval, schema output, prompt, evidence và bước kiểm tra sau sinh.

Việc fine-tune toàn bộ reasoning của LLM trên một tập dữ liệu nhỏ hoặc nhãn sinh tự động thường không phải lựa chọn tối ưu cho v1, vì mô hình có thể học vẹt các trường hợp đã gặp, tốn tài nguyên và khó xác định lỗi thật sự nằm ở đâu. Với financial event extraction, nếu chỉ train hoặc prompt end-to-end mà không kiểm soát workflow, hệ thống vẫn có thể sai khi:

- bài báo đầu vào bị parse sai hoặc thiếu metadata.
- context retrieval đưa vào các bài không liên quan.
- prompt không ràng buộc schema.
- mô hình sinh field không có evidence.
- hệ thống không có bước verification để phát hiện hallucination.

Do đó, hướng tiếp cận của đề tài là tối ưu workflow trước: dữ liệu được làm sạch, chunking có cấu trúc, retrieval kết hợp BM25/vector/metadata, reranking lọc evidence, pattern refs gắn với chunk cung cấp ví dụ đúng schema và verification loại bỏ thông tin không có căn cứ. Nếu evaluation cho thấy một bước cụ thể là điểm nghẽn, project mới cân nhắc fine-tune module nhỏ tại đúng bước đó, ví dụ reranker, event detector hoặc event type classifier.

Do đó, đóng góp chính của đề tài là thiết kế một **workflow NLP có căn cứ bằng chứng** cho financial event extraction tiếng Việt. LLM là một thành phần trong pipeline, không phải toàn bộ phương pháp.

## Mục tiêu nghiên cứu

Đề tài hướng đến các mục tiêu:

1. Xây dựng tập dữ liệu mới về tin doanh nghiệp tiếng Việt.
2. Thiết kế schema/taxonomy cho bài toán trích xuất sự kiện tài chính.
3. Xây dựng workflow NLP có evidence grounding để giảm hallucination.
4. So sánh nhiều cấu hình retrieval, embedding, reranking, prompting và schema nhãn.
5. Đánh giá định lượng bằng retrieval metrics và extraction metrics.
6. Xây dựng demo app để minh họa khả năng ứng dụng.

## Phạm vi

Project v1 tập trung vào:

- báo tài chính tiếng Việt công khai.
- sự kiện doanh nghiệp liên quan cổ phiếu/doanh nghiệp niêm yết.
- output dạng bảng/JSON.
- evaluation trên AI-generated gold labels pass auto validation.

Project v1 không làm:

- dự đoán giá cổ phiếu.
- khuyến nghị mua/bán.
- định giá doanh nghiệp.
- xử lý mạng xã hội nhiễu cao.
- fine-tune toàn bộ LLM 8B.

## Câu hỏi nghiên cứu

Các câu hỏi chính:

1. Retrieval có giúp mô hình 8B trích xuất sự kiện chính xác và ít hallucination hơn không?
2. Hybrid retrieval và reranking có tốt hơn semantic search đơn thuần không?
3. Schema có subtype và event arguments chi tiết có giúp output hữu ích hơn cho phân tích đầu tư không?
4. Verification dựa trên evidence có giảm hallucination mà vẫn giữ được recall không?
5. Workflow nhiều bước có hiệu quả hơn prompting trực tiếp LLM không?
