# 05 - Database Browser

## Mục Tiêu

Database Browser giúp xem dữ liệu đang có trong PostgreSQL mà không cần mở
pgAdmin hoặc viết SQL thủ công. Đây là màn hình quan trọng để kiểm tra pipeline
có thật sự lưu dữ liệu đúng hay không.

## Nguyên Tắc

- V1 chủ yếu read-only.
- Không hiển thị secret.
- Không hiển thị vector full nếu quá dài; chỉ hiển thị dimension, model, status.
- Có pagination bắt buộc.
- Có detail drawer để xem JSON đầy đủ.
- Có link giữa các bảng liên quan.

## Tables Cần Xem

### Articles

Mục đích: kiểm tra bài báo đã ingest.

Columns:

- article_id;
- source;
- title;
- published_at;
- url;
- text_word_count;
- tickers_hint;
- event_type_hints;
- content_hash.

Filters:

- source;
- ticker;
- event type hint;
- published date;
- search title/text.

Detail drawer:

- full text preview;
- metadata JSON;
- link chunks;
- link gold label;
- link extraction results.

### Article Metadata

Mục đích: xem metadata bổ sung.

Columns:

- article_id;
- metadata key;
- metadata value;
- created_at.

### Chunks

Mục đích: debug retrieval.

Columns:

- chunk_id;
- article_id;
- chunk_level;
- chunk_index;
- text preview;
- tickers_hint;
- event_keywords;
- event_type_hints.

Detail drawer:

- full chunk text;
- parent chunk;
- paragraph range;
- source article link.

### Chunk Embeddings

Mục đích: kiểm tra embedding đã lưu.

Columns:

- embedding_id;
- chunk_id;
- embedding_model;
- embedding_dimension;
- status;
- cache_hit;
- created_at.

Không render vector đầy đủ trong table.

Detail drawer:

- vector length;
- first 8 values preview;
- content hash;
- chunk link.

### Gold Labels

Mục đích: xem teacher labels đã accepted.

Columns:

- article_id;
- document_label;
- event_count;
- teacher_model;
- validation_status;
- prompt_version.

Detail drawer:

- events table;
- raw label JSON;
- validation errors.

### Patterns

Mục đích: kiểm tra pattern records và chunk-pattern mapping.

Columns:

- pattern_id;
- article_id;
- document_label;
- event_type;
- event_subtype;
- ticker;
- score nếu có.

Detail drawer:

- input excerpt;
- gold output;
- explanation brief;
- embedding metadata.

### Extraction Runs

Mục đích: xem output student 8B.

Columns:

- run_id;
- article_id;
- status;
- document_label;
- event_count;
- student_model;
- prompt_version;
- created_at.

Detail drawer:

- event table;
- selected patterns;
- retrieval trace;
- node traces;
- validation issues;
- verification report;
- raw JSON.

### Node Traces

Mục đích: debug workflow node.

Columns:

- run_id;
- node;
- status;
- latency_ms;
- warnings;
- errors.

Detail drawer:

- input summary;
- output summary;
- full warnings/errors.

### Ticker Dictionary

Mục đích: kiểm tra mapping ticker-company.

Columns:

- ticker;
- company_name;
- aliases;
- sector;
- exchange;
- status;
- last_verified_at.

Actions:

- search;
- add/update ticker nếu dùng API hiện có;
- bulk import sau.

## API Cần Có

Mỗi entity nên có:

```text
GET /admin/db/{entity}?limit=50&offset=0&query=...
GET /admin/db/{entity}/{id}
```

Entity names:

- `articles`
- `chunks`
- `embeddings`
- `gold-labels`
- `patterns`
- `extraction-runs`
- `node-traces`
- `tickers`

## UX Chi Tiết

Table:

- sticky header;
- compact rows;
- search input;
- filter chips;
- pagination;
- copy ID button;
- open detail button.

Detail drawer:

- tabs nếu object phức tạp;
- pretty JSON viewer;
- link sang related records.

## Performance

- Không query toàn bộ bảng.
- Default limit 50.
- Max limit 200.
- Text search nên dùng indexed columns trước.
- JSON detail chỉ load khi mở drawer.
