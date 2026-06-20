# M05: Pattern Library

## Mục tiêu

M05 tạo thư viện pattern/few-shot examples từ `events_gold.jsonl` để hỗ trợ workflow
sinh bảng sự kiện ở các milestone sau. Gold labels ở đây là nhãn do AI teacher sinh ra
và đã qua auto validation từ M02; project không có bước human review lại nhãn. Nếu
record pass validation tự động thì được chấp nhận làm gold label cho pattern library.

Mục tiêu kỹ thuật:

- Chuyển mỗi gold event thành một pattern có `input_excerpt`, `gold_output`,
  `event_type`, `event_subtype`, `evidence_span`, `event_arguments`.
- Tạo pattern riêng cho `NO_EVENT` để giảm false positive khi bài viết chỉ là nhận định
  thị trường chung.
- Embed `pattern_text` và lưu artifact JSONL có thể sync lên PostgreSQL + pgvector.
- Chọn top pattern theo dense similarity, metadata overlap và rule/diversity rerank.
- Render selected patterns thành few-shot prompt block dùng được cho LLM extraction.

## Input

```text
data/processed/articles_clean.jsonl
data/labels/events_gold.jsonl
data/schema/event_taxonomy_v1.json
```

## Output

Runtime artifacts:

```text
data/patterns/patterns.jsonl
data/patterns/patterns_rejected.jsonl
data/patterns/pattern_embeddings.jsonl
data/patterns/pattern_embedding_cache.jsonl
reports/evaluation/pattern_metrics.csv
reports/evaluation/pattern_library_summary.md
```

Version-controlled files:

```text
src/finevent/patterns/
infra/postgres/005_event_patterns.sql
tests/test_pattern_library.py
```

## Công nghệ

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Pattern build | Python dataclass + JSONL | Biến gold labels thành pattern records để test offline, debug và sync DB |
| Auto validation | Taxonomy loader `data/schema/event_taxonomy_v1.json` | Đảm bảo event type/subtype hợp lệ, `HAS_EVENT` có evidence, `NO_EVENT` có `events=[]` |
| Embedding offline | `HashEmbeddingClient` | Baseline deterministic cho smoke test, CI/local test không cần network |
| Embedding production | Cloudflare Workers AI qua client M03 | Dùng cùng model embedding với retrieval khi chạy thật |
| Pattern store | In-memory `PatternStore` | Chọn few-shot patterns bằng dense + metadata + rule score |
| Storage dài hạn | PostgreSQL + pgvector | Lưu `event_patterns` và `event_pattern_embeddings` để phục vụ app/API lâu dài |
| CLI | `python -m finevent.patterns` | Chạy build, search, render few-shot, sync PostgreSQL độc lập |
| Testing | pytest + ruff | Kiểm chứng build, embedding cache, selection, prompt rendering và pipeline artifact |

## Cấu trúc pattern

Một pattern hợp lệ gồm các trường chính:

```json
{
  "pattern_id": "pattern_...",
  "article_id": "...",
  "document_label": "HAS_EVENT",
  "pattern_kind": "event",
  "event_type": "EXPANSION",
  "event_subtype": "NEW_FACTORY",
  "ticker": "HPG",
  "company_name": "Hoa Phat Group",
  "impact_sentiment": "POSITIVE",
  "input_excerpt": "...",
  "gold_output": {
    "document_label": "HAS_EVENT",
    "events": []
  },
  "pattern_text": "...",
  "evidence_span": "...",
  "event_arguments": {},
  "explanation_brief": "...",
  "teacher_model": "fixture_teacher",
  "teacher_prompt_version": "m02_teacher_v1",
  "auto_validation_status": "PASS",
  "validation_errors": []
}
```

`pattern_text` không embed toàn bộ bài báo. Nó gồm các phần có giá trị cho few-shot:

```text
Document label
Title/source
Ticker/company
Event type/subtype
Impact sentiment
Evidence
Summary
Arguments
```

## Workflow build

1. Đọc `articles_clean.jsonl` và `events_gold.jsonl`.
2. Map article theo `article_id`.
3. Với `HAS_EVENT`, tạo một pattern cho từng event trong label.
4. Với `NO_EVENT`, tạo một pattern không có event để dạy model khi nào không nên sinh bảng.
5. Validate pattern bằng taxonomy:
   - `event_type` phải nằm trong taxonomy.
   - `event_subtype` phải hợp lệ với `event_type`.
   - `HAS_EVENT` phải có `evidence_span`.
   - `NO_EVENT` phải có `events=[]`.
6. Ghi pattern hợp lệ vào `data/patterns/patterns.jsonl`.
7. Ghi pattern lỗi vào `data/patterns/patterns_rejected.jsonl`.
8. Embed pattern hợp lệ và cache theo `embedding_model + pattern_hash`.
9. Đánh giá pattern selection và ghi metrics.

## Workflow search và few-shot selection

Khi workflow extraction cần lấy ví dụ mẫu, M05 chạy:

1. Tạo `PatternQuery` từ bài báo mới hoặc raw query:
   - title/text preview.
   - ticker hints.
   - company hints.
   - event keywords.
   - event type/subtype hints.
2. Embed query text bằng cùng embedding family với pattern store.
3. Tính điểm cho từng pattern:
   - `dense_score`: cosine similarity trên vector.
   - `metadata_score`: ticker/company/event type/event subtype/keyword overlap.
   - `rule_score`: boost `HAS_EVENT` nếu query có tín hiệu sự kiện, boost `NO_EVENT`
     nếu query chung chung.
4. Tính final score:

```text
score = 0.60 * dense_score + 0.30 * metadata_score + 0.10 * rule_score
```

5. Diversity rerank:
   - mặc định top 3 pattern.
   - tối đa top 5 pattern.
   - giới hạn số pattern cùng `event_type` để prompt không bị lệch về một class.
6. Render few-shot block:
   - input excerpt.
   - expected output JSON.
   - explanation brief.
   - cảnh báo LLM không được copy factual value nếu input mới không có evidence.

## PostgreSQL schema

Migration:

```text
infra/postgres/005_event_patterns.sql
```

Bảng chính:

- `event_patterns`: lưu pattern text, gold output, metadata, taxonomy label và validation status.
- `event_pattern_embeddings`: lưu vector embedding theo `pattern_id + embedding_model`.

Index quan trọng:

- `event_type`
- `event_subtype`
- `ticker`
- `document_label`
- GIN index cho `gold_output` và `metadata`

## CLI

Build pattern library:

```powershell
$env:PYTHONPATH='src'
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.patterns build `
  --articles-path data\processed\articles_clean.jsonl `
  --gold-path data\labels\events_gold.jsonl `
  --embedding-dimension 128
```

Search pattern:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.patterns search `
  --query "HPG khoi cong nha may moi mo rong san xuat" `
  --ticker HPG `
  --event-type EXPANSION `
  --top-k 3
```

Nếu `patterns.jsonl` được embed bằng Cloudflare, search/render cũng phải dùng cùng
embedding provider:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.patterns search `
  --query "HPG khoi cong nha may moi mo rong san xuat" `
  --ticker HPG `
  --event-type EXPANSION `
  --query-embedding-provider cloudflare `
  --query-embedding-model "@cf/baai/bge-m3" `
  --query-embedding-dimension 1024
```

Render few-shot prompt:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.patterns render-few-shot `
  --query "HPG khoi cong nha may moi mo rong san xuat" `
  --ticker HPG `
  --event-type EXPANSION `
  --top-k 3
```

Sync PostgreSQL:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m finevent.patterns sync-postgres
```

## Metrics

`reports/evaluation/pattern_metrics.csv` hiện có các metric:

| Metric | Ý nghĩa |
| --- | --- |
| `pattern_count` | Số pattern hợp lệ được đưa vào library |
| `event_pattern_count` | Số pattern có sự kiện |
| `no_event_pattern_count` | Số pattern `NO_EVENT` |
| `event_type_coverage` | Số event type có pattern đại diện |
| `event_subtype_coverage` | Số event subtype có pattern đại diện |
| `avg_selected_patterns` | Số pattern trung bình được trả về khi search |
| `mrr` | Rank của pattern đúng trong self-query smoke evaluation |
| `same_type_recall_at_3/5` | Top K có pattern cùng event type hay không |
| `same_subtype_recall_at_3/5` | Top K có pattern cùng event subtype hay không |

## Test

```powershell
$env:PYTHONPATH='src'
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests\test_pattern_library.py
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m ruff check src\finevent\patterns tests\test_pattern_library.py
```

Test coverage M05:

- Build pattern từ AI gold labels, không human review.
- Build cả `HAS_EVENT` và `NO_EVENT`.
- Embedding cache reuse theo `pattern_hash`.
- Pattern selection trả về đúng event type/ticker.
- Render few-shot có input excerpt và expected JSON.
- Full pipeline ghi đủ artifact và metric.

## Done Criteria

- `python -m finevent.patterns build` chạy thành công.
- `data/patterns/patterns.jsonl` có pattern hợp lệ.
- `data/patterns/pattern_embeddings.jsonl` có embedding tương ứng.
- `reports/evaluation/pattern_metrics.csv` có metric aggregate.
- `python -m finevent.patterns search` trả về pattern phù hợp.
- `python -m finevent.patterns render-few-shot` render prompt block đúng format.
- `pytest` và scoped `ruff` pass.

## Ghi chú mở rộng

Khi dataset lớn hơn, cần bổ sung:

- Ít nhất 50 pattern pass validation.
- Pattern cho tối thiểu 6 event type.
- Pattern cho các class hiếm như `LEGAL_RISK`, `DEBT_CREDIT`, `MARKET_LISTING`.
- Thực nghiệm few-shot lift: zero-shot extraction vs pattern-augmented extraction.
- Ablation: dense only vs metadata-aware vs diversity rerank.
