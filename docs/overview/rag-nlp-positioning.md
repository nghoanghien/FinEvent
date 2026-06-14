# RAG and NLP Positioning

## Mục tiêu

Tài liệu này giải thích cách định vị project để phù hợp với nhóm **xử lý ngôn ngữ tự nhiên** dù hệ thống có sử dụng nhiều kỹ thuật RAG.

Kết luận chính: project không nên được trình bày là một app RAG hỏi đáp. Project nên được trình bày là một **evidence-grounded NLP pipeline for Vietnamese financial event extraction**. RAG là tầng truy xuất bằng chứng và giảm hallucination, còn lõi NLP là phát hiện sự kiện, phân loại loại sự kiện, trích xuất slot và kiểm định output có căn cứ.

## Vì sao không gọi là naive RAG

Naive RAG thường gồm:

1. Cắt văn bản theo số token cố định.
2. Dùng một embedding model mặc định.
3. Semantic search top K.
4. Nhét context vào prompt.
5. Tin output LLM.

Cách này không đủ mạnh cho đồ án NLP/Deep Learning vì gần như chỉ cấu hình thư viện.

FinEvent-VN dùng hướng **Advanced NLP-RAG**:

1. Làm sạch dữ liệu và bóc tách metadata tài chính.
2. Chunking có chiến lược theo cấu trúc bài báo.
3. So sánh nhiều embedding model.
4. Hybrid retrieval giữa BM25, dense vector và metadata.
5. Multi-stage retrieval và reranking.
6. LLM reasoning rerank để lọc context theo logic sự kiện doanh nghiệp.
7. Prompt có citation, grounded instruction và self-verification.
8. Output được validate bằng schema, evidence và taxonomy.
9. Đánh giá bằng retrieval metrics, extraction metrics và ablation study.

## Cách trình bày trước hội đồng NLP

Nên dùng cách diễn đạt:

> Đề tài xây dựng một hệ thống trích xuất thông tin có cấu trúc từ báo tài chính tiếng Việt. Retrieval được dùng như một module truy xuất evidence và pattern để hỗ trợ mô hình ngôn ngữ nhỏ trích xuất có căn cứ, không phải là mục tiêu cuối cùng của project.

Các bài toán NLP chính:

| Bài toán con | Vai trò trong project |
| --- | --- |
| Text cleaning | Chuẩn hóa bài báo tiếng Việt |
| Metadata extraction | Bóc tách nguồn, ngày đăng, công ty, ticker |
| Event detection | Xác định bài có sự kiện doanh nghiệp hay không |
| Event classification | Dự đoán `event_type` và `event_subtype` |
| Slot filling | Điền `event_arguments` theo taxonomy |
| Sentiment orientation | Dự đoán `impact_sentiment` |
| Evidence grounding | Mỗi field quan trọng phải có bằng chứng |
| Hallucination reduction | Loại field không được context hỗ trợ |
| Evaluation | Đo retrieval, extraction và groundedness |

## Kỹ thuật RAG có thể áp dụng

### 1. Structure-aware chunking

Áp dụng được và nên làm.

Bài báo tài chính thường có title, sapo, đoạn thân bài, bullet, bảng số liệu và phần liên quan. Không nên chunk cố định tùy tiện. Chunk nên tôn trọng ranh giới đoạn và metadata.

Giá trị NLP:

- Giữ nguyên ngữ cảnh ngôn ngữ tự nhiên.
- Giảm việc cắt đứt evidence span.
- Giúp slot filling chính xác hơn.

### 2. Hierarchical chunking

Áp dụng được.

Lưu nhiều cấp:

- document-level representation
- section-level representation
- paragraph/chunk-level representation

Khi retrieval:

1. Tìm bài liên quan ở cấp document.
2. Tìm đoạn evidence ở cấp chunk.
3. Đưa cả metadata bài và đoạn evidence vào extraction.

### 3. So sánh nhiều embedding model

Áp dụng được và nên đưa vào thí nghiệm.

Nhóm model đề xuất:

- Cloudflare embedding đang có sẵn.
- BGE-M3.
- Multilingual E5.
- GTE multilingual.
- Một embedding model tiếng Việt nếu đủ thời gian.

Metric:

- Recall@K.
- MRR.
- nDCG@K.
- End-to-end event F1 sau khi dùng context retrieval.

### 4. Fine-tune embedding theo domain

Áp dụng được nhưng nên để optional.

Với dataset v1 nhỏ, fine-tune embedding có thể tốn công và dễ overfit. Có thể trình bày là hướng mở rộng hoặc milestone nâng cao:

- Dùng cặp positive: hai bài cùng event type/ticker/sự kiện.
- Dùng cặp negative: khác event type hoặc cùng ticker nhưng không cùng sự kiện.
- Train bằng contrastive loss hoặc triplet loss.

### 5. Hybrid retrieval

Áp dụng được và nên làm.

Kết hợp:

- BM25: bắt từ khóa rõ như `trúng thầu`, `phát hành`, `bổ nhiệm`.
- Dense retrieval: bắt tương đồng ngữ nghĩa.
- Metadata-aware retrieval: ưu tiên cùng ticker, công ty, nguồn, thời gian.

### 6. Query rewriting và query decomposition

Áp dụng được.

Từ một bài báo đầu vào, tạo nhiều truy vấn:

- truy vấn theo ticker
- truy vấn theo tên công ty
- truy vấn theo event trigger words
- truy vấn theo event type dự đoán sơ bộ
- truy vấn theo đối tác/dự án nếu có

Sau đó hợp nhất kết quả để tránh bỏ sót evidence.

### 7. Multi-stage retrieval

Áp dụng được.

Pipeline đề xuất:

1. Stage 1: retrieve rộng top 50 bằng BM25 + dense.
2. Stage 2: metadata/rule rerank còn top 20.
3. Stage 3: LLM reasoning rerank còn top 3-5.
4. Stage 4: đưa context tốt nhất vào extraction.

### 8. Fine-tune reranker hoặc extract model

Áp dụng được nhưng để optional hoặc phần nâng cao.

Ưu tiên v1:

- rule-aware rerank
- LLM reasoning rerank
- lightweight classifier trên embedding

Nếu có thời gian:

- train reranker nhỏ dự đoán relevance.
- train classifier nhỏ cho `HAS_EVENT`, `event_type` hoặc relevance.
- thử Cross Entropy, Weighted Cross Entropy, Focal Loss.

### 9. Citation prompting và grounded prompting

Áp dụng bắt buộc.

Mỗi event phải có:

- `evidence_span`
- `source_url`
- `article_id`
- confidence

Prompt phải nói rõ: không được sinh field nếu không có bằng chứng trong article/context.

### 10. Self-verification

Áp dụng bắt buộc.

Sau khi sinh JSON, chạy bước verify:

1. Field có đúng schema không?
2. Event type/subtype có hợp lệ không?
3. Evidence span có thật trong article/context không?
4. Argument có được evidence hỗ trợ không?
5. Có dấu hiệu hallucination không?

## Kỹ thuật không nên ưu tiên v1

| Kỹ thuật | Lý do |
| --- | --- |
| Fine-tune toàn bộ LLM 8B | Dữ liệu nhỏ, dễ overfit, tốn tài nguyên |
| Đưa mạng xã hội vào ngay | Nhiễu cao, khó đánh giá |
| Chỉ dùng LangChain chain đơn giản | Dễ bị xem là app engineering, thiếu NLP contribution |
| Dùng duy nhất semantic search | Không đủ thí nghiệm và dễ bỏ sót từ khóa tài chính |
| Không rerank, không verification | Không đáp ứng yêu cầu hallucination reduction |

## Luận điểm bảo vệ

Khi báo cáo, có thể chốt như sau:

> RAG trong project này không thay thế bài toán NLP. RAG đóng vai trò retrieval evidence, còn trọng tâm nghiên cứu là structured information extraction cho miền tài chính tiếng Việt. Project đánh giá riêng retrieval quality và extraction quality, đồng thời có verification để giảm hallucination.

