# Backend API Documentation

Backend API dùng FastAPI để phục vụ Next.js admin dashboard và các thao tác vận
hành pipeline. Tài liệu này mô tả implementation hiện tại, không chỉ là contract
ý tưởng.

## Cách đọc

| File | Vai trò |
| --- | --- |
| [01-overview.md](01-overview.md) | Mục tiêu, kiến trúc router, cách chạy local |
| [02-endpoints.md](02-endpoints.md) | Danh sách endpoint v1 và input/output chính |
| [03-job-runner.md](03-job-runner.md) | Cơ chế chạy workflow, logs, cancel và artifact tracking |
| [04-security-and-artifacts.md](04-security-and-artifacts.md) | Path allowlist, error format, không expose secrets |

## Module Code Chính

```text
src/finevent/api/
  main.py
  admin_health.py
  admin_reports.py
  admin_runs.py
  admin_db.py
  admin_outputs.py
  job_runner.py
  artifacts.py
  errors.py
  serialization.py
```

## Lệnh Chạy

```powershell
$env:PYTHONPATH="src"
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m uvicorn finevent.api.main:app --reload --host 127.0.0.1 --port 8000
```

Sau khi chạy, mở:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/admin/health
```
