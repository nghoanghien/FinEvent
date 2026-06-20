# ADR-0001: Chiến lược Database Layer

## Trạng thái

Accepted.

## Bối cảnh

Từ M01 đến M06, project đã có nhiều bảng PostgreSQL và nhiều module sync dữ liệu:

- ticker dictionary.
- AI-generated gold labels.
- retrieval documents/chunks/embeddings.
- pattern library.
- extraction run logs.

Các module này hiện dùng SQLAlchemy engine nhưng viết câu lệnh SQL trực tiếp bằng
`sqlalchemy.text()`. Cách này phù hợp ở giai đoạn dựng pipeline vì các thao tác chủ yếu là:

- bulk sync JSONL vào PostgreSQL.
- `INSERT ... ON CONFLICT`.
- cast JSONB rõ ràng.
- pgvector literal insert.
- batch workflow cần tường minh và dễ debug.

Tuy nhiên, nếu project tiếp tục mở rộng sang API/backend, dashboard, evaluation UI và nhiều quan hệ bảng hơn, việc chỉ dùng Raw SQL sẽ làm schema khó quản lý hơn, dễ lệch tên cột và khó sinh migration có kiểm soát.

## Quyết định

Không chuyển toàn bộ code hiện tại sang ORM ngay.

Project chọn chiến lược nâng cấp theo tầng:

1. Giữ Raw SQL hiện tại cho các workflow batch đã chạy ổn.
2. Thêm `finevent.database.catalog` làm catalog nhẹ, không phụ thuộc SQLAlchemy.
3. Thêm `finevent.database.schema` dùng SQLAlchemy Core metadata để làm schema registry trung tâm.
4. Thêm Alembic skeleton để chuẩn bị quản lý migration dài hạn.
5. Chỉ dùng ORM/SQLModel có chọn lọc khi API/backend thật sự cần object relationship rõ ràng.

## Lý do

Raw SQL vẫn tốt cho các thao tác sau:

- upsert phức tạp.
- bulk insert/sync.
- JSONB cast.
- pgvector insert.
- các đoạn SQL cần kiểm soát chính xác.

SQLAlchemy Core phù hợp cho:

- schema metadata dùng chung.
- Alembic autogenerate về sau.
- repository layer.
- query có điều kiện động trong API/backend.

ORM hoặc SQLModel chỉ nên dùng cho:

- API đọc lịch sử extraction run.
- quan hệ `ExtractionRun -> ExtractionNodeTrace`.
- quan hệ `FinancialNewsDocument -> FinancialNewsChunk`.
- dashboard/backend cần object graph.

Không dùng ORM chỉ để thay thế mọi câu SQL hiện tại nếu câu SQL đang ngắn, rõ và đã test được.

## Hệ quả

Tích cực:

- Không phá các milestone M01-M06.
- Pipeline offline vẫn chạy khi chưa cài SQLAlchemy/Alembic.
- Có đường nâng cấp rõ sang Alembic và repository layer.
- Giữ được tính tường minh cho các câu upsert và pgvector.

Đánh đổi:

- Trong ngắn hạn tồn tại song song Raw SQL và SQLAlchemy Core metadata.
- Cần test để catalog/metadata không lệch migration SQL.
- Nếu schema thay đổi, người triển khai phải cập nhật cả migration và metadata.

## Triển khai hiện tại

Các thành phần đã thêm:

```text
src/finevent/database/
  __init__.py
  catalog.py
  engine.py
  schema.py

alembic.ini
infra/alembic/
  env.py
  script.py.mako
  versions/.gitkeep
```

Optional dependency:

```toml
db = [
  "alembic>=1.13",
  "psycopg[binary]>=3.2",
  "sqlalchemy>=2.0",
]
```

Cách cài khi cần DB/Alembic:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pip install -e ".[db]"
```

## Nguyên tắc áp dụng về sau

- Raw SQL sync modules hiện tại không refactor ồ ạt nếu chưa có lợi ích rõ.
- Migration SQL hiện có trong `infra/postgres` vẫn là nguồn triển khai đã ổn định cho M01-M06.
- Alembic dùng cho các migration mới sau khi schema registry ổn định.
- SQLAlchemy Core metadata phải được giữ khớp với các bảng chính.
- ORM/SQLModel chỉ thêm khi có use case API/backend cụ thể.

## Kiểm thử

Test liên quan:

```text
tests/test_database_foundation.py
```

Các test cần đảm bảo:

- import `finevent.database` không yêu cầu SQLAlchemy.
- catalog bao phủ các bảng trong `infra/postgres/001-006`.
- Alembic skeleton tồn tại.
- nếu cài SQLAlchemy, Core metadata khớp catalog.
