# Article Query and Extraction Workflow

## Mục tiêu

Workflow này xử lý một bài báo mới do user nhập URL hoặc paste text, sau đó sinh bảng sự kiện doanh nghiệp có cấu trúc.

Khác với [rag-preparation-workflow.md](../data/rag-preparation-workflow.md), workflow này chạy online trong demo app hoặc khi batch evaluate.

## Input

```json
{
  "input_type": "url",
  "value": "https://example.com/hpg-trung-thau-du-an-moi",
  "run_config": {
    "retrieval": "hybrid_metadata_llm_rerank",
    "pattern_count": 3,
    "student_model": "qwen_or_llama_8b",
    "prompt_version": "extract_v1"
  }
}
```

Nếu user paste text:

```json
{
  "input_type": "text",
  "value": "Nội dung bài báo...",
  "metadata": {
    "title": "HPG trúng thầu dự án...",
    "source_url": null,
    "published_at": null
  }
}
```

## Output

```json
{
  "article_id": "input_20260614_001",
  "document_label": "HAS_EVENT",
  "events": [
    {
      "event_id": "input_20260614_001_e01",
      "ticker": "HPG",
      "company_name": "Hoa Phat",
      "event_type": "CONTRACT",
      "event_subtype": "BIDDING_WIN",
      "event_summary": "HPG trúng thầu gói cung cấp thép cho dự án...",
      "event_arguments": {
        "partner": "...",
        "contract_value": "...",
        "project": "...",
        "product": "thép"
      },
      "impact_sentiment": "POSITIVE",
      "evidence_span": "HPG trúng thầu gói cung cấp thép...",
      "confidence": 0.82
    }
  ],
  "retrieval_trace": [],
  "verification_report": {},
  "warnings": []
}
```

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| Workflow orchestration | LangGraph |
| Article parsing | parser từ data workflow |
| Query rewriting | rule + optional LLM |
| Retrieval | BM25 + ChromaDB |
| Reranking | rule-aware + LLM reasoning rerank |
| Pattern selection | ChromaDB collection `event_patterns` |
| Extraction | student LLM 7B/8B |
| Validation | Pydantic/JSON Schema |
| Logging | JSONL + SQLite `extraction_runs` |

## LangGraph state

State nên có dạng:

```json
{
  "run_id": "run_001",
  "input_article": {},
  "clean_article": {},
  "query_plan": {},
  "retrieved_candidates": [],
  "reranked_contexts": [],
  "selected_patterns": [],
  "draft_extraction": {},
  "verification_report": {},
  "final_output": {},
  "warnings": [],
  "errors": []
}
```

## Workflow chi tiết

### Node 1: Input normalization

Nhiệm vụ:

- Nếu input là URL, crawl và parse bài.
- Nếu input là text, chuẩn hóa thành article object.
- Sinh `article_id`.
- Chuẩn hóa Unicode, whitespace, ngày tháng nếu có.

Output:

```json
{
  "article_id": "input_20260614_001",
  "title": "...",
  "text": "...",
  "source_url": "...",
  "published_at": "...",
  "content_hash": "sha256:..."
}
```

### Node 2: Metadata and event hint extraction

Nhiệm vụ:

- Nhận diện ticker/company hints bằng dictionary.
- Tìm event trigger words.
- Dự đoán sơ bộ event type hint bằng rule nhẹ.

Output:

```json
{
  "tickers_hint": ["HPG"],
  "company_names_hint": ["Hoa Phat"],
  "event_keywords": ["trúng thầu"],
  "event_type_hints": ["CONTRACT"]
}
```

### Node 3: Query rewriting

Tạo nhiều truy vấn để retrieval không bị phụ thuộc một câu query duy nhất.

Ví dụ:

```json
{
  "queries": [
    {
      "name": "ticker_event_query",
      "text": "HPG trúng thầu hợp đồng dự án",
      "weight": 1.0
    },
    {
      "name": "company_query",
      "text": "Hoa Phat ký hợp đồng cung cấp thép",
      "weight": 0.8
    },
    {
      "name": "event_type_query",
      "text": "doanh nghiệp trúng thầu hợp đồng lớn",
      "weight": 0.6
    }
  ]
}
```

### Node 4: Query decomposition

Tách bài toán retrieval thành các mục tiêu nhỏ:

| Sub-query | Mục tiêu |
| --- | --- |
| Same company | Tìm bài cùng doanh nghiệp |
| Same event type | Tìm pattern cùng loại sự kiện |
| Same actor/action | Tìm bài có cùng hành động |
| Same project/partner | Tìm evidence nếu có tên dự án/đối tác |

Kết quả các sub-query được hợp nhất trước khi rerank.

### Node 5: Hybrid retrieval

Chạy song song:

- BM25 trên title + body + event keywords.
- Dense retrieval trên ChromaDB.
- Metadata filter theo ticker/source/time nếu có.

Điểm gợi ý:

```text
hybrid_score =
  0.45 * dense_score
+ 0.30 * bm25_score
+ 0.15 * ticker_or_company_bonus
+ 0.10 * recency_or_source_bonus
```

Output stage 1: top 50 candidates.

### Node 6: Rule-aware rerank

Rerank nhanh bằng rule:

- cùng ticker hoặc company: cộng điểm.
- có event keyword trùng: cộng điểm.
- cùng event type hint: cộng điểm.
- chỉ là tin giá/thị trường chung: trừ điểm.
- context quá ngắn hoặc thiếu evidence: trừ điểm.

Output stage 2: top 20 candidates.

### Node 7: LLM reasoning rerank

LLM đọc ứng viên tốt nhất và trả về nhận định có cấu trúc.

Prompt kiểm tra:

1. Bài ứng viên có sự kiện doanh nghiệp cụ thể không?
2. Actor chính là ai?
3. Event type/subtype là gì?
4. Sự kiện có cùng công ty, cùng loại hoặc cùng logic với bài đầu vào không?
5. Nguyên nhân/bối cảnh sự kiện là gì?
6. Evidence span nào hỗ trợ?
7. Có phải tin phân tích chung, tin giá cổ phiếu hoặc nhận định thị trường không?

Output:

```json
{
  "candidate_article_id": "cafef_hpg_001",
  "has_corporate_event": true,
  "candidate_event_type": "CONTRACT",
  "same_or_related_company": true,
  "same_or_related_event_type": true,
  "evidence_span": "HPG trúng thầu...",
  "reasoning_summary": "Ứng viên cùng nói về HPG và sự kiện trúng thầu.",
  "relevance_label": "HIGH",
  "relevance_score": 0.91
}
```

Output stage 3: top 3-5 contexts.

### Node 8: Pattern selection

Chọn pattern từ `event_patterns`.

Ưu tiên:

1. Cùng `event_type`.
2. Cùng `event_subtype`.
3. Cùng ticker/company nếu có.
4. Có event_arguments tương tự.
5. Có output JSON pass validation.

Không đưa quá nhiều pattern vào prompt. Mặc định top 3.

### Node 9: Event extraction

Student LLM nhận:

- article gốc
- context đã rerank
- patterns
- schema rút gọn
- taxonomy event type/subtype
- argument rules

LLM phải sinh JSON theo [event-schema.md](../../schema/event-schema.md).

Prompt bắt buộc:

```text
Only extract information supported by the article or retrieved evidence.
Every event must include evidence_span.
If the article does not contain a concrete corporate event, return NO_EVENT.
Return valid JSON only.
```

### Node 10: Verification and repair

Gọi workflow [verification-hallucination-workflow.md](verification-hallucination-workflow.md).

Nếu lỗi nhẹ:

- sửa JSON format
- map enum sai chính tả về enum hợp lệ
- yêu cầu chọn lại evidence

Nếu lỗi nặng:

- loại event không có evidence
- hạ confidence
- trả `NO_EVENT` nếu tất cả event đều unsupported

### Node 11: Final formatting

Trả output cho app:

- bảng event
- evidence citations
- retrieval trace
- warnings
- confidence
- diagnostics

## Metrics

| Metric | Ý nghĩa |
| --- | --- |
| End-to-end latency | Thời gian từ input đến output |
| Event detection F1 | Có/không có event |
| Event type macro-F1 | Đúng loại sự kiện |
| Event subtype accuracy | Đúng subtype khi có |
| Slot-level F1 | Đúng event arguments |
| Evidence support rate | Field có evidence |
| Hallucinated field rate | Field không có evidence |
| JSON validity rate | Output parse được |
| Repair success rate | Lỗi được sửa sau repair |

## Acceptance Criteria

- Với bài `HAS_EVENT`, output có ít nhất một event đúng schema.
- Với bài `NO_EVENT`, không ép sinh event.
- Mỗi event có `evidence_span`.
- App hiển thị được retrieval trace và verification report.
- Mọi run được lưu vào `extraction_runs` hoặc JSONL log.
