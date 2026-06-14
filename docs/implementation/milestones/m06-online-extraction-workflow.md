# M6: Online Article Extraction Workflow

## Mục tiêu

Xây workflow online từ URL/text bài báo đến bảng sự kiện JSON. Đây là workflow chính của demo app và evaluation end-to-end.

## Input

```json
{
  "input_type": "url",
  "value": "https://example.com/news",
  "run_config": {
    "retrieval": "hybrid_metadata_llm_rerank",
    "pattern_count": 3,
    "student_model": "qwen_or_llama_8b"
  }
}
```

## Output

```json
{
  "article_id": "input_001",
  "document_label": "HAS_EVENT",
  "events": [],
  "retrieval_trace": [],
  "verification_report": {},
  "warnings": []
}
```

## Công nghệ

- LangGraph để điều phối workflow.
- Student LLM 7B/8B.
- ChromaDB + BM25.
- Pattern library.
- Pydantic/JSON Schema.
- JSONL/SQLite run logs.

## Cách triển khai chi tiết

### Bước 1: Thiết kế LangGraph state

State nên có:

- input article.
- clean article.
- metadata hints.
- query plan.
- retrieved candidates.
- reranked contexts.
- selected patterns.
- draft extraction.
- verified output.
- warnings/errors.

### Bước 2: Node preprocess

Nếu input là URL:

- fetch HTML.
- parse title/body/date/source.
- normalize text.

Nếu input là text:

- tạo article object.
- source_url null.

### Bước 3: Node metadata hints

Extract:

- ticker/company hints.
- event keywords.
- event type hints.
- article length/warnings.

### Bước 4: Node query rewriting/decomposition

Tạo nhiều query:

- same company query.
- same event type query.
- event trigger query.
- partner/project query nếu có.

### Bước 5: Node retrieve/rerank

Gọi retrieval engine:

1. BM25 + dense stage.
2. metadata-aware score.
3. rule-aware rerank.
4. optional LLM reasoning rerank.

### Bước 6: Node pattern selection

Chọn top 3 patterns theo event hint/context.

### Bước 7: Node extraction

Prompt student LLM với:

- schema rút gọn.
- taxonomy.
- article.
- retrieved contexts.
- patterns.
- instruction chỉ dùng evidence.

Output phải là JSON, không markdown.

### Bước 8: Node validation/repair

Parse JSON, sửa lỗi format nhẹ, check enum.

Verification sâu nằm ở milestone M7 nhưng node này có thể gọi sang verifier.

### Bước 9: Logging

Log mỗi node:

- input/output.
- latency.
- errors.
- model/prompt/config version.

## Kiểm thử

- Test workflow với một bài `HAS_EVENT`.
- Test workflow với một bài `NO_EVENT`.
- Test model trả JSON lỗi thì repair không crash.
- Test retrieval empty vẫn chạy zero-shot với warning.

## Metrics

- JSON validity rate.
- event detection F1.
- event type macro-F1.
- slot-level F1.
- latency.
- cost per article.

## Done Criteria

- Workflow chạy từ input đến output.
- Có retrieval trace.
- Có selected patterns.
- Có draft và final output.
- Có log từng node.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
| --- | --- |
| LangGraph state phình quá lớn | Chỉ lưu raw text dài ở artifact, state lưu ID/path |
| LLM trả markdown | Repair hoặc constrained output |
| Context quá dài | Giới hạn top context và excerpt |
| Bài nhiều event | Cho phép nhiều event records |

