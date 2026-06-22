# 04 - Security And Artifact Access

## Error Format

API lỗi trả cùng một dạng:

```json
{
  "error_code": "ARTIFACT_NOT_FOUND",
  "message": "Artifact path does not exist.",
  "details": {
    "path": "reports/evaluation/..."
  }
}
```

## Path Allowlist

Các endpoint đọc file chỉ cho phép path trong:

```text
data/
reports/
runs/
```

Các path sau bị chặn:

```text
../../.env
reports/../.env
C:\Users\OWNER\...
```

Lý do: frontend cần đọc report/artifact, nhưng không được đọc `.env`, source code
nhạy cảm hoặc file ngoài workspace.

## Không Expose Secret

`/admin/health` chỉ trả:

```text
configured / unconfigured
```

cho teacher LLM, student LLM và embedding provider. API không trả API key, DSN,
header auth hoặc nội dung `.env`.

## Admin API Key

Mặc định `/admin/*` yêu cầu:

```text
X-Admin-API-Key: <FINEVENT_ADMIN_API_KEY>
```

Backend so sánh key bằng `hmac.compare_digest()` thay vì so sánh chuỗi thường.

Nếu chưa cấu hình `FINEVENT_ADMIN_API_KEY`, API trả:

```json
{
  "error_code": "ADMIN_AUTH_NOT_CONFIGURED",
  "message": "Admin API key is required..."
}
```

Nếu key sai hoặc thiếu:

```json
{
  "error_code": "ADMIN_AUTH_REQUIRED",
  "message": "Admin API requires a valid X-Admin-API-Key header."
}
```

Chỉ dùng biến sau cho local dev tạm thời:

```text
FINEVENT_ADMIN_AUTH_DISABLED=true
```

Không bật biến này khi demo qua network hoặc deploy frontend public.

## CORS Allowlist

Backend chỉ cho origins trong:

```text
FINEVENT_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Header `X-Admin-API-Key` được đưa vào allow headers để Next.js frontend gọi được
admin API.

## DB Browser Safety

`/admin/db/{entity}` không nhận tên bảng trực tiếp. Backend map `entity` sang
SQLAlchemy table bằng allowlist.

Entity hợp lệ:

- `articles`;
- `chunks`;
- `embeddings`;
- `gold-labels`;
- `gold-events`;
- `patterns`;
- `extraction-runs`;
- `node-traces`;
- `tickers`.

Embedding vector không được trả full trong detail endpoint để tránh response quá
lớn.

## Job Runner Safety

Frontend không gửi command line thô. Backend tự build command từ whitelist
workflow:

- `evaluation`;
- `student_batch_extraction`;
- `student_batch_with_evaluation`.

Runner có thêm:

- `FINEVENT_MAX_CONCURRENT_RUNS` để giới hạn subprocess chạy song song;
- `FINEVENT_MAX_QUEUE_SIZE` để giới hạn số run chờ;
- startup reconciliation để đổi run cũ `queued/running` thành `interrupted`.

Nếu cần thêm workflow mới, thêm vào `finevent.api.job_runner.build_workflow_steps`
và viết test tương ứng.

## Test Coverage

Test hiện có:

```text
tests/test_admin_api.py
```

Các case chính:

- `/admin/health`;
- list reports;
- đọc Markdown;
- parse CSV;
- parse JSONL;
- list chart groups;
- đọc extraction output từ filesystem;
- chặn path traversal;
- bắt buộc admin API key;
- queue full trả 429;
- startup reconciliation đánh dấu run cũ là interrupted;
- list runs;
- reject unknown workflow.
