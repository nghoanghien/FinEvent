# Live M00-M08 Runbook

Runbook này dùng cho luồng chạy thật, không dùng DB fallback.

## 1. Chuẩn bị môi trường

```powershell
conda activate deep-learning-project
python -m pip install -e ".[dev,config,db,ingestion,rag,workflow,llm,notebook,evaluation]"
Copy-Item .env.example .env
```

Điền secret vào `.env`:

- `OPENAI_API_KEY`: API key teacher LLM.
- `TEACHER_LLM_MODEL`: ví dụ `gpt-4o-mini`.
- `STUDENT_LLM_API_KEY`: API key endpoint self-host.
- `EMBEDDING_API_KEY`: API key endpoint embedding self-host.

## 2. Khởi động PostgreSQL + pgvector

```powershell
docker compose up -d postgres
python -m finevent.database.cli healthcheck
python -m finevent.database.cli apply-migrations
python -m finevent.database.cli verify-pgvector
```

Nếu `verify-pgvector` lỗi thì dừng lại và sửa Docker/Postgres trước. Không chuyển sang SQLite hoặc vector fallback.

Mặc định project map PostgreSQL ra host port `55433` để tránh đụng PostgreSQL local ở `5432`.

## 3. Smoke test API

Mở `api-smoke-test.ipynb` và chạy từ trên xuống. Notebook chỉ kiểm tra:

- teacher LLM gán nhãn thử;
- student 8B trả lời thử;
- embedding trả vector và dimension.

## 4. Chạy toàn bộ M00-M08 trên 25 bài

```powershell
python -m finevent.ops.cli run-m00-m08 --max-articles 25
```

Artifact chính:

- `data/processed/articles_clean.jsonl`
- `data/labels/events_gold.jsonl`
- `data/retrieval/chunk_embeddings.jsonl`
- `data/patterns/patterns.jsonl`
- `runs/extraction/<run_id>/result.json`
- `reports/live_m00_m08_summary.json`
- `reports/evaluation/`

## 5. Chạy từng milestone khi cần debug

```powershell
python -m finevent.ingestion --discover --max-download-articles 25 --sync-postgres
python -m finevent.labeling generate-prompts --limit 25
python -m finevent.labeling run-teacher --max-records 25
python -m finevent.labeling validate
python -m finevent.labeling sync-postgres
python -m finevent.rag prepare --embedding-provider direct_http --embedding-dimension 1024
python -m finevent.rag sync-postgres
python -m finevent.retrieval compare --query-embedding-provider direct_http --query-embedding-dimension 1024
python -m finevent.patterns build --embedding-provider direct_http --embedding-dimension 1024
python -m finevent.patterns sync-postgres
python -m finevent.extraction run-article --article-id <article_id> --student-provider env --sync-postgres --retrieval-query-embedding-provider direct_http --retrieval-query-embedding-dimension 1024 --pattern-query-embedding-provider direct_http --pattern-query-embedding-dimension 1024
python -m finevent.evaluation run
```
