# M0: Project Setup

## Mục tiêu

Tạo nền kỹ thuật cho toàn bộ project: cấu trúc thư mục, config, logging, test skeleton và convention artifact. Milestone này không xử lý NLP phức tạp, nhưng quyết định project có dễ mở rộng, debug và tái lập hay không.

## Vì sao cần làm trước

Các milestone sau đều cần gọi model, ghi artifact và chạy nhiều cấu hình thí nghiệm. Nếu không chuẩn hóa config/logging ngay từ đầu, mỗi script sẽ lưu output một kiểu, rất khó so sánh metric và viết báo cáo.

## Input

- Repo trống hoặc repo chỉ có `docs/`.
- Các API key dự kiến: Cloudflare embedding, teacher LLM, student LLM nếu dùng API.

## Output

```text
configs/
  default.yaml
  logging.yaml
.env.example
environment.yml
pyproject.toml
requirements.lock
src/
  finevent/
    __init__.py
    config.py
    logging_utils.py
    paths.py
tests/
  test_config.py
runs/
data/
reports/
```

## Công nghệ

- Python 3.11+.
- Miniconda + `environment.yml` để quản lý Python environment và dependency ML/NLP.
- `uv` để compile/sync pip dependencies bên trong conda env đã activate.
- `pyproject.toml` để lưu package metadata, dependency groups, Ruff/Pyright/pytest config.
- `requirements.lock` để khóa dependency Python đã resolve.
- YAML config bằng `pyyaml` hoặc `ruamel.yaml`.
- `.env` bằng `python-dotenv`.
- Logging dạng JSONL bằng `logging` chuẩn hoặc `structlog`.
- Test bằng `pytest`.
- Docker Compose cho PostgreSQL + pgvector.

## Cách triển khai chi tiết

### Bước 1: Tạo cấu trúc thư mục code

Tạo môi trường bằng Miniconda:

```bash
conda env create -f environment.yml
conda activate finevent-vn
uv pip compile pyproject.toml -o requirements.lock
uv pip sync requirements.lock
```

Trong project này, Miniconda là tool tạo môi trường. `uv` chỉ dùng nhóm lệnh `uv pip ...` sau khi đã activate conda env, không dùng `uv sync` làm mặc định để tránh tạo thêm `.venv` riêng.

Khi cần chạy test/dev tools, cài nhóm dependency dev từ `pyproject.toml`:

```bash
uv pip compile pyproject.toml --extra dev --extra config -o requirements-dev.lock
uv pip sync requirements-dev.lock
python -m pytest
```

Tạo package chính `src/finevent/` để chứa core logic. Không đặt logic vào notebook hoặc frontend Next.js.

Các module nền:

- `config.py`: load YAML + env.
- `paths.py`: chuẩn hóa đường dẫn artifact.
- `logging_utils.py`: tạo run logger.
- `types.py`: type aliases hoặc dataclass dùng chung nếu cần.

### Bước 2: Tạo config mặc định

`configs/default.yaml` nên có các nhóm:

```yaml
project:
  name: finevent-vn
  timezone: Asia/Bangkok

storage:
  postgres_dsn: postgresql+psycopg://finevent:password@localhost:5432/finevent
  vector_backend: pgvector
  raw_dir: data/raw
  processed_dir: data/processed
  labels_dir: data/labels
  vector_store_dir: data/vector_store

models:
  embedding_default: cloudflare
  teacher_model: teacher_llm
  student_model: qwen_or_llama_8b

retrieval:
  top_k_stage1: 50
  top_k_stage2: 20
  top_k_final: 5

logging:
  run_dir: runs
```

### Bước 3: Tạo `.env.example`

Không commit API key thật. Chỉ ghi tên biến:

```text
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
TEACHER_LLM_API_KEY=
STUDENT_LLM_ENDPOINT=
POSTGRES_DSN=
```

### Bước 4: Tạo run ID và logging convention

Mọi script cần ghi:

- `run_id`
- `timestamp`
- `config_path`
- `git_commit` nếu lấy được
- `input_artifact`
- `output_artifact`
- `status`
- `error` nếu fail

### Bước 5: Tạo script smoke test

Script `python -m finevent.hello_pipeline` chỉ cần:

1. Load config.
2. Tạo `run_id`.
3. Ghi một log JSONL.
4. In đường dẫn run log.

## Kiểm thử

- `python -m pytest tests/test_config.py`.
- Test load config thành công.
- Test `.env.example` không chứa secret thật.
- Test tạo được run log trong `runs/`.
- Test `uv pip sync requirements.lock` chạy trong conda env đã activate.

## Metrics / Done Criteria

- Config load được trên máy local.
- Script smoke test chạy được.
- Log có đầy đủ `run_id`, `timestamp`, `config_version`.
- Không có API key thật trong repo.

## Lỗi thường gặp

| Lỗi | Cách tránh |
| --- | --- |
| Hard-code path Windows | Dùng `pathlib.Path` |
| Hard-code API key | Dùng `.env` |
| Mỗi script log một kiểu | Dùng chung `logging_utils.py` |
| `uv` tạo `.venv` riêng ngoài conda env | Dùng `uv pip ...` sau khi `conda activate finevent-vn` |
| Frontend chứa hết logic | Core workflow phải ở backend `src/finevent/`, frontend chỉ gọi API |
