# Chạy Local Stack FinEvent bằng Docker Compose

Docker Compose là cách chạy chính thức cho môi trường local của project. Một lệnh sẽ bật đầy đủ database, backend API và frontend admin.

## Kiến trúc runtime

| Service | Container | Công nghệ | Cổng host mặc định | Vai trò |
| --- | --- | --- | --- | --- |
| `postgres` | `finevent-postgres` | `pgvector/pgvector:pg16` | `55433 -> 5432` | Lưu bài báo, metadata, nhãn, vector embedding, workflow runs và output |
| `backend` | `finevent-backend` | FastAPI + Uvicorn | `18000 -> 8000` | Admin API, job runner, DB browser, reports, outputs, migration DB lúc khởi động |
| `frontend` | `finevent-frontend` | Next.js + TypeScript | `3000 -> 3000` | Giao diện admin để chạy workflow, xem log, xem DB, xem report và output cấu trúc |

Backend dùng host port `18000` thay vì `8000` để tránh xung đột với các phần mềm local thường chiếm port `8000`. Bên trong Docker network, backend vẫn chạy cổng `8000`.

## File cấu hình

Root `.env` chứa secret thật và cấu hình runtime backend/model/database. Không commit file này.

Nếu chưa có `.env`, copy từ `.env.example` hoặc chạy script start để tự tạo:

```powershell
copy .env.example .env
```

Các biến cần điền thủ công:

```text
OPENAI_API_KEY=
STUDENT_LLM_API_KEY=
EMBEDDING_API_KEY=
```

`FINEVENT_ADMIN_API_KEY` sẽ được script start tự sinh nếu đang thiếu. Nếu chạy `docker compose up --build` trực tiếp thì bạn nên tự điền biến này trước.

Các biến port mặc định:

```text
BACKEND_PORT=18000
FRONTEND_PORT=3000
NEXT_PUBLIC_FINEVENT_API_BASE_URL=http://127.0.0.1:18000
```

`frontend/admin/.env.local` chỉ phục vụ chế độ chạy frontend native. Docker Compose truyền `NEXT_PUBLIC_FINEVENT_API_BASE_URL` trực tiếp qua environment của service `frontend`.

Không đưa `FINEVENT_ADMIN_API_KEY` vào frontend env vì mọi biến `NEXT_PUBLIC_*` có thể xuất hiện trong browser bundle. Admin key được nhập tại `/admin/settings` và lưu trong `localStorage`.

## Chạy full stack

Cách chính, dùng Docker Compose trực tiếp:

```powershell
docker compose up --build
```

Nếu muốn chạy detached:

```powershell
docker compose up --build -d
```

Wrapper tiện ích trên Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-stack.ps1
```

Wrapper này chỉ làm các việc phụ trợ:

1. Tạo `.env` từ `.env.example` nếu chưa có.
2. Sinh `FINEVENT_ADMIN_API_KEY` nếu thiếu.
3. Tạo `frontend/admin/.env.local` cho chế độ frontend native.
4. Dừng các dev server native cũ của chính project nếu đang giữ port frontend.
5. Gọi `docker compose up -d --build`.
6. Chờ healthcheck và smoke test backend/frontend.

## Backend startup trong container

Container backend không bật API ngay lập tức. Entrypoint `infra/docker/backend-entrypoint.sh` chạy theo thứ tự:

1. Chờ PostgreSQL nhận kết nối.
2. Chạy `python -m finevent.database.cli apply-migrations`.
3. Chạy `python -m finevent.database.cli verify-pgvector`.
4. Khởi động `uvicorn finevent.api.main:app`.

Cách này đảm bảo API chỉ healthy khi database schema và extension `pgvector` đã sẵn sàng.

## Kiểm tra trạng thái

```powershell
docker compose ps
```

Hoặc dùng wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/status-local-stack.ps1
```

Các URL chính:

```text
Admin UI:      http://localhost:3000/admin
Backend:       http://127.0.0.1:18000
Backend health: http://127.0.0.1:18000/health
```

Sau khi frontend mở lên, vào:

```text
http://localhost:3000/admin/settings
```

Điền:

| Trường | Giá trị |
| --- | --- |
| FastAPI base URL | `http://127.0.0.1:18000` |
| Admin API key | Giá trị của `FINEVENT_ADMIN_API_KEY` trong root `.env` |

Sau đó bấm test health. Nếu thành công, các màn hình Runs, Reports, Database và Outputs sẽ gọi được backend.

## Xem log

```powershell
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

Xem 100 dòng cuối:

```powershell
docker compose logs --tail 100 backend
```

## Dừng stack

Giữ dữ liệu database:

```powershell
docker compose down
```

Hoặc dùng wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local-stack.ps1
```

Xóa luôn volume database và cache frontend:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local-stack.ps1 -RemoveVolumes
```

Chỉ dùng `-RemoveVolumes` khi bạn thật sự muốn xóa dữ liệu local.

## Ghi chú phát triển

- Backend mount `src`, `configs`, `infra/postgres`, `infra/alembic`, `data`, `reports`, `runs` từ máy host vào container để code, migration và artifact local luôn đồng bộ.
- Frontend mount `frontend/admin` vào container, nhưng giữ `node_modules` và `.next` trong Docker named volumes để tránh lỗi khác biệt hệ điều hành.
- Nếu đổi port backend, cập nhật đồng thời `BACKEND_PORT` và `NEXT_PUBLIC_FINEVENT_API_BASE_URL`.
- Nếu backend migration có lỗi, xem `docker compose logs backend`; API sẽ không healthy cho đến khi migration/pgvector pass.
