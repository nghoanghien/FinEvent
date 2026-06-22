# 01 - Backend API Overview

## Mục tiêu

Backend API là lớp trung gian giữa Next.js admin dashboard và core Python
pipeline. Frontend không đọc file trực tiếp, không gọi CLI trực tiếp và không giữ
secret model/API key.

API v1 tập trung vào các nhu cầu vận hành thật:

- bảo vệ admin endpoints bằng API key;
- kiểm tra trạng thái môi trường;
- xem report, bảng CSV, JSONL, biểu đồ;
- xem output extraction có cấu trúc;
- duyệt dữ liệu trong PostgreSQL qua entity allowlist;
- chạy workflow bằng job runner có log persistence;
- stream log để UI hiển thị tiến trình giống notebook/Colab.

## Kiến trúc Router

| Router | Prefix | Vai trò |
| --- | --- | --- |
| `admin_health.py` | `/admin/health` | Kiểm tra API, DB, pgvector, artifact dirs, model env |
| `admin_reports.py` | `/admin/reports` | Xem Markdown/CSV/JSONL/SVG/PNG reports |
| `admin_runs.py` | `/admin/runs` | Tạo run, xem run, xem log, stream log, cancel |
| `admin_db.py` | `/admin/db` | DB browser qua entity allowlist |
| `admin_outputs.py` | `/admin/outputs` | Xem structured extraction outputs |
| `main.py` | `/health`, `/dictionary/tickers` | Health cũ và ticker dictionary API |

## Cách Chạy Local

Chạy trong conda env hiện tại:

```powershell
$env:PYTHONPATH="src"
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m uvicorn finevent.api.main:app --reload --host 127.0.0.1 --port 8000
```

Nếu muốn API đọc artifact từ workspace khác:

```powershell
$env:FINEVENT_WORKSPACE_ROOT="C:\Users\OWNER\source\Deep Learning Project"
```

Mặc định API dùng current working directory làm workspace root.

## Dependency

API cần optional extra:

```powershell
python -m pip install -e ".[api]"
```

Trong project hiện tại, các dependency chính gồm:

| Công nghệ | Dùng để làm gì |
| --- | --- |
| FastAPI | Định nghĩa HTTP API và OpenAPI docs |
| Pydantic | Validate request body |
| python-dotenv | Load `.env` cho admin API key và runtime env khi chạy local |
| SQLAlchemy Core | Query PostgreSQL cho DB browser và ticker dictionary |
| Uvicorn | Chạy local dev server |
| JSONL/CSV stdlib | Parse artifact report không cần service ngoài |

## Env Quan Trọng

```text
FINEVENT_ADMIN_API_KEY=change-me
FINEVENT_ADMIN_AUTH_DISABLED=false
FINEVENT_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
FINEVENT_MAX_CONCURRENT_RUNS=1
FINEVENT_MAX_QUEUE_SIZE=20
```

Frontend gọi `/admin/*` cần gửi:

```text
X-Admin-API-Key: <FINEVENT_ADMIN_API_KEY>
```

`FINEVENT_ADMIN_AUTH_DISABLED=true` chỉ dùng cho local dev tạm thời. Không nên bật
trong lúc demo qua network hoặc khi frontend public.

Khi chạy Uvicorn từ repo root, backend sẽ load `.env` một lần nếu `python-dotenv`
được cài qua extra `api`.

## Nguyên tắc thiết kế

- Không cho frontend gửi arbitrary shell command.
- Không expose `.env`, API key, DSN.
- File artifact chỉ được đọc trong `data/`, `reports/`, `runs/`.
- DB browser chỉ cho đọc các entity đã whitelist.
- `/admin/*` yêu cầu `X-Admin-API-Key`.
- CORS chỉ mở cho origins trong `FINEVENT_ALLOWED_ORIGINS`.
- Job runner có queue và giới hạn số run chạy song song.
- FastAPI startup đánh dấu run cũ `queued/running` thành `interrupted`.
- Job runner lưu logs vào `runs/admin/{run_id}/logs/events.jsonl`.
- Endpoint report/output vẫn xem được artifact filesystem khi PostgreSQL chưa bật.
