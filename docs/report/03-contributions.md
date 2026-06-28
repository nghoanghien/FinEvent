# 3. Đóng Góp Chính Của Đề Tài

Đây là phần quan trọng nhất khi viết báo cáo và bảo vệ. Contribution cần được trình bày như các đóng góp kỹ thuật có thể kiểm chứng, không chỉ là “xây app dùng LLM”.

## Tóm tắt contribution

FinEvent-VN có 3 đóng góp chính:

1. **Schema/taxonomy cho financial corporate event extraction tiếng Việt**: định nghĩa output có cấu trúc, taxonomy sự kiện, subtype, argument fields và evidence.
2. **Dataset tiếng Việt bằng weak supervision**: thu thập bài báo tài chính mới và tạo AI-generated gold labels bằng teacher LLM kết hợp auto validation.
3. **Workflow-first evidence-grounded NLP pipeline**: thiết kế workflow hoàn chỉnh để tăng độ chính xác và giảm hallucination, gồm RAG preparation, hybrid retrieval, reranking, pattern selection, schema-guided extraction, verification, evaluation và tối ưu đúng điểm nghẽn.

Cách trình bày này gọn hơn việc tách retrieval, reranking, verification, evaluation thành các contribution riêng lẻ. Những phần đó đều là các cải tiến nằm trong cùng một đóng góp lớn: **xây dựng workflow NLP có căn cứ bằng chứng để trích xuất sự kiện chính xác hơn**.

## Contribution 1: Vietnamese Financial Corporate Event Schema

### Đóng góp là gì

Đề tài thiết kế một schema có cấu trúc để biểu diễn sự kiện doanh nghiệp từ báo tài chính tiếng Việt. Schema không chỉ có `event_type`, mà còn có:

- `event_subtype`.
- `event_arguments`.
- `impact_sentiment`.
- `evidence_span`.
- `confidence`.
- `event_attributes` nếu chạy cấu trúc nhãn đa nhãn.

Taxonomy bao phủ nhiều nhóm sự kiện:

- M&A.
- hợp đồng/trúng thầu.
- tăng vốn/phát hành.
- thay đổi lãnh đạo.
- mở rộng sản xuất/thị trường.
- pháp lý/rủi ro.
- hợp tác chiến lược.
- cấp phép/phê duyệt.
- kết quả kinh doanh.
- giao dịch tài sản.
- nợ/vay/trái phiếu.
- cổ tức/cổ đông.
- sản phẩm/dịch vụ.
- niêm yết/giao dịch.
- ESG/rủi ro vận hành.

### Vì sao đáng giá

Nếu chỉ yêu cầu LLM “tạo bảng”, output dễ không ổn định: mỗi lần sinh một kiểu, field lúc có lúc không. Schema giúp:

- chuẩn hóa output.
- đánh giá định lượng từng field.
- dùng được cho database.
- hỗ trợ slot filling.
- kiểm soát hallucination bằng evidence.

### Khác gì phương pháp đơn giản

Baseline đơn giản:

```text
Prompt: "Hãy đọc bài báo và tóm tắt sự kiện thành bảng."
```

Nhược điểm:

- không có taxonomy cố định.
- không có subtype.
- không có argument rules theo event type.
- khó đánh giá F1.
- dễ bịa thông tin không có evidence.

FinEvent-VN:

- có taxonomy và schema rõ.
- mỗi event type có argument fields phù hợp.
- output validate được.
- đo được field-level metric.

### Cách chứng minh

Trong báo cáo, chứng minh bằng:

- bảng schema.
- bảng taxonomy.
- ví dụ output JSON.
- tỷ lệ JSON/schema validity.
- slot-level F1 hoặc argument coverage.

## Contribution 2: AI-generated Vietnamese Financial Event Dataset

### Đóng góp là gì

Đề tài thu thập tập bài báo tài chính tiếng Việt mới và tạo AI-generated gold labels bằng teacher LLM. Gold labels được chấp nhận khi pass auto validation, không human review.

Dataset gồm:

- raw articles.
- clean articles.
- metadata.
- chunks.
- event labels.
- evidence spans.
- pattern examples.

### Vì sao đáng giá

Dữ liệu tiếng Việt cho financial event extraction không phổ biến như các dataset tiếng Anh. Việc tạo một dataset miền tài chính Việt Nam giúp:

- có dữ liệu mới đúng yêu cầu môn học.
- có benchmark nội bộ để so sánh workflow.
- có pattern refs gắn với chunk cho grounded extraction.
- có nền cho các nghiên cứu sau.

### Khác gì chỉ dùng dataset cũ

Nếu dùng dataset cũ:

- có thể không đúng miền tài chính Việt Nam.
- không có ticker/company Việt Nam.
- không có taxonomy phù hợp thị trường Việt Nam.
- ít giá trị ứng dụng cho bài toán cổ phiếu Việt Nam.

FinEvent-VN tạo dữ liệu theo đúng domain:

- báo tài chính tiếng Việt.
- doanh nghiệp niêm yết Việt Nam.
- event taxonomy sát ngữ cảnh đầu tư.

### Điểm cần trung thực

Vì không human review, báo cáo cần ghi rõ:

- labels là AI-generated gold.
- auto validation kiểm tra schema/evidence.
- metric đo độ khớp với AI-generated labels, không tương đương nhãn chuyên gia.

Điều này không làm mất giá trị project, miễn là trình bày đúng: đây là weak supervision để giảm chi phí gán nhãn thủ công.

### Cách chứng minh

Báo cáo cần có:

- số bài thu thập.
- số bài clean.
- số bài pass labeling.
- phân bố event type.
- tỷ lệ `NO_EVENT`.
- auto validation pass rate.
- ví dụ nhãn.

## Contribution 3: Workflow-first Evidence-grounded NLP Pipeline

### Đóng góp là gì

Đóng góp lớn nhất về phương pháp của đề tài là thiết kế một workflow hoàn chỉnh để đưa kết quả trích xuất chính xác hơn, thay vì chỉ prompt end-to-end hoặc fine-tune lại toàn bộ mô hình.

Workflow gồm:

```text
Data cleaning
-> structure-aware chunking
-> embedding/BM25 indexes
-> query rewriting/decomposition
-> hybrid retrieval
-> reranking
-> pattern selection
-> schema-guided LLM extraction
-> evidence verification
-> structured event table
-> evaluation and ablation
```

Trong contribution này, retrieval, reranking, verification, evaluation và fine-tune điểm nghẽn không nên được xem là các đóng góp rời rạc. Chúng là các thành phần phối hợp để hoàn thiện một mục tiêu chung: **tạo workflow kiểm soát được dữ liệu, context, output schema và evidence để tăng độ chính xác của hệ thống**.

### Vì sao workflow-first phù hợp với đề tài

Trong financial event extraction, output sai có thể đến từ nhiều nguồn:

- bài báo bị parse sai hoặc mất đoạn quan trọng.
- chunking cắt mất câu chứa evidence.
- retrieval đưa vào bài cùng chủ đề nhưng khác sự kiện.
- prompt không ràng buộc schema đủ chặt.
- LLM sinh argument nghe hợp lý nhưng không có trong bài.
- không có bước verification để phát hiện hallucination.

Nếu fine-tune toàn bộ reasoning end-to-end ngay từ đầu, rất khó biết mô hình đang sửa lỗi nào. Với dữ liệu nhỏ và nhãn weak supervision, cách đó còn dễ học theo các mẫu đã gặp mà không cải thiện đúng điểm nghẽn. Vì vậy, đề tài chọn hướng:

1. Thiết kế workflow có các bước rõ ràng.
2. Đo lỗi ở từng bước.
3. Cải thiện đúng module gây lỗi.
4. Chỉ fine-tune module nhỏ nếu metric chứng minh cần thiết.

### Thành phần 3.1: RAG preparation có cấu trúc

Đề tài không dùng chunking cố định tùy tiện. Corpus được chuẩn bị bằng:

- cleaning và metadata normalization.
- structure-aware chunking theo title, sapo, paragraph, bullet.
- hierarchical representation: document, section, paragraph.
- embedding index bằng pgvector.
- FAISS baseline cho ablation.
- BM25 index cho lexical retrieval.

Giá trị của phần này là đảm bảo retrieval hoạt động trên dữ liệu sạch, có metadata và ít làm mất evidence.

### Thành phần 3.2: Hybrid retrieval và reranking

Retrieval trong workflow không chỉ là semantic search. Hệ thống kết hợp:

- BM25 để bắt keyword tài chính như `trúng thầu`, `phát hành`, `bổ nhiệm`.
- dense vector retrieval để bắt tương đồng ngữ nghĩa.
- metadata-aware scoring theo ticker, company, source, time.
- query rewriting và query decomposition.
- rule-aware rerank.
- LLM reasoning rerank để kiểm tra logic sự kiện.

Trong domain tài chính, hai bài có thể giống nhau về chủ đề nhưng không cùng sự kiện. Ví dụ một bài nói giá cổ phiếu HPG tăng, bài khác nói HPG trúng thầu. Semantic similarity có thể kéo cả hai, nhưng chỉ bài thứ hai có corporate event cụ thể. Reranking giúp lọc context thật sự liên quan trước khi đưa vào extraction.

### Thành phần 3.3: Pattern selection và schema-guided extraction

Pattern library cung cấp các ví dụ đã pass auto validation. Khi xử lý bài mới, hệ thống chọn pattern gần nhất theo event type, metadata và event arguments.

Mục tiêu:

- giúp LLM theo đúng schema.
- giảm lỗi format JSON.
- giúp model phân biệt `HAS_EVENT` và `NO_EVENT`.
- tạo output nhất quán hơn giữa các bài.

Extraction không yêu cầu model tự do suy luận toàn bộ. Model được ràng buộc bởi:

- schema.
- taxonomy.
- retrieved evidence.
- selected patterns.
- instruction chỉ sinh field có bằng chứng.

### Thành phần 3.4: Verification và hallucination reduction

Sau extraction, workflow kiểm tra:

- JSON validity.
- schema compliance.
- evidence span matching.
- argument grounding.
- taxonomy consistency.
- contradiction check.
- self-verification nếu cần.

Unsupported fields bị loại hoặc set null. Event không có evidence bị drop hoặc hạ confidence. Đây là phần quan trọng để hệ thống không tin hoàn toàn vào output LLM.

Với tài chính, hallucination có rủi ro cao vì field bịa như giá trị hợp đồng, tên đối tác, mã cổ phiếu hoặc quyết định pháp lý có thể gây hiểu lầm. Verification buộc output phải quay lại văn bản nguồn.

### Thành phần 3.5: Evaluation và ablation theo từng bước

Workflow chỉ có ý nghĩa nếu chứng minh được bằng metric. Vì vậy đề tài xây evaluation framework gồm:

Retrieval metrics:

- Recall@K.
- Precision@K.
- MRR.
- nDCG.

Extraction metrics:

- event detection F1.
- event type macro-F1.
- subtype accuracy.
- ticker accuracy.
- slot-level F1.
- impact sentiment macro-F1.

Output quality metrics:

- JSON validity.
- schema compliance.
- hallucination rate.
- evidence coverage.

Ablation study cần so sánh:

| Cấu hình | Mục đích |
| --- | --- |
| Direct prompt | Baseline end-to-end |
| Dense retrieval only | Tác động semantic retrieval |
| Hybrid retrieval | Tác động BM25 + vector + metadata |
| Hybrid + rerank | Tác động reranking |
| Hybrid + context pattern refs | Tác động pattern refs gắn với retrieved chunks |
| Hybrid + pattern + verification | Tác động workflow đầy đủ |

### Thành phần 3.6: Tối ưu đúng điểm nghẽn thay vì train toàn bộ

Đề tài không loại bỏ hoàn toàn training/fine-tuning, nhưng không xem fine-tune toàn bộ model là bước đầu tiên. Cách làm hợp lý hơn là:

1. chạy workflow baseline.
2. log lỗi từng bước.
3. xác định điểm nghẽn.
4. chỉ train module nhỏ ở đúng điểm nghẽn nếu cần.

Ví dụ:

- nếu false positive `HAS_EVENT` cao, train event detector.
- nếu retrieval top K nhiễu, train reranker nhỏ.
- nếu nhầm event type nhiều, train event type classifier.

Cách này phù hợp hơn với dữ liệu nhỏ vì nó tập trung tài nguyên vào lỗi đo được, thay vì train lại toàn bộ chuỗi reasoning mà không biết lỗi đến từ đâu.

### Khác gì naive RAG hoặc prompt trực tiếp

Naive RAG:

- chunk cố định.
- một embedding model.
- semantic search top K.
- nhét context vào prompt.
- không rerank.
- không đánh giá retrieval.
- không verification.

Prompt trực tiếp:

- nhanh để tạo baseline.
- nhưng output dễ không ổn định.
- khó biết field nào có evidence.
- khó phân tích lỗi theo module.

FinEvent-VN:

- xử lý dữ liệu có cấu trúc.
- truy hồi bằng hybrid retrieval.
- rerank theo logic sự kiện.
- chọn pattern đúng schema.
- extraction có ràng buộc.
- verification sau sinh.
- evaluation từng module.

### Cách chứng minh contribution workflow

Báo cáo nên có bảng:

| Run | Retrieval | Pattern | Verification | Event F1 | Type F1 | Hallucination |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | none | off | off | | | |
| R2 | dense | off | off | | | |
| R3 | hybrid | on | off | | | |
| R4 | hybrid + rerank | on | on | | | |

Kết luận mong muốn:

- retrieval cải thiện khả năng tìm evidence.
- reranking giảm context nhiễu.
- pattern cải thiện JSON/schema consistency.
- verification giảm hallucination.
- workflow đầy đủ tốt hơn direct prompt trên các metric chính.

## Cách viết contribution trong báo cáo

Không nên viết:

> Đề tài dùng RAG và LLM để trích xuất sự kiện.

Nên viết:

> Đề tài đề xuất một workflow NLP có căn cứ bằng chứng cho bài toán trích xuất sự kiện doanh nghiệp tiếng Việt. Workflow kết hợp schema sự kiện chuyên biệt, dữ liệu weak supervision, retrieval nhiều tầng, reranking, pattern selection, schema-guided extraction và verification dựa trên evidence. Hệ thống được đánh giá bằng cả retrieval metrics, extraction metrics và hallucination metrics.

## Cách bảo vệ khi bị hỏi “có gì mới?”

Trả lời theo 3 tầng:

1. **Schema mới cho domain**: taxonomy/subtype/arguments phù hợp sự kiện doanh nghiệp Việt Nam.
2. **Dữ liệu mới**: corpus báo tài chính tiếng Việt và AI-generated event labels.
3. **Workflow extraction có kiểm chứng**: advanced retrieval + reranking + pattern + extraction + verification + ablation, không phải prompt đơn giản.

Nếu cần nhấn mạnh phần workflow:

> Điểm chính của đề tài không phải là chỉ dùng LLM, mà là thiết kế một workflow đo được lỗi và sửa đúng điểm nghẽn. Retrieval, reranking, pattern selection, extraction, verification và evaluation đều phục vụ cùng một mục tiêu: đưa ra bảng sự kiện chính xác hơn và có evidence.

## Cách bảo vệ khi bị hỏi “RAG có phải NLP không?”

Trả lời:

> Trong đề tài này, RAG không phải mục tiêu cuối. RAG là module retrieval evidence trong một pipeline NLP trích xuất thông tin. Các bài toán NLP lõi gồm event detection, event classification, slot filling, evidence grounding và hallucination reduction. Retrieval được đánh giá riêng bằng Recall@K/MRR/nDCG, còn extraction được đánh giá bằng F1 và field-level metrics.
