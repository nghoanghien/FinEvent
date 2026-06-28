# 13 - Bộ Soạn Graph Milestone

Tài liệu này mô tả graph composer hiện tại ở `/admin/runs`. Trang này không còn dùng
preset workflow kèm textarea JSON raw. UI hydrate workflow catalog từ backend, dựng
milestone graph bằng React Flow, cho admin chọn node hợp lệ, cấu hình node đã chọn
bằng form, rồi tạo run `milestone_graph`.

## Sơ Đồ Code

```text
frontend/admin/src/features/runs/
  RunsPage.tsx
  workflow-composer/
    catalog.ts
    index.ts
    state.ts
    types.ts
    hooks/
      useWorkflowCatalog.ts
      useWorkflowComposer.ts
    components/
      ConfigField.tsx
      ConfigModal.tsx
      NodeConfigDrawer.tsx
      NodeConfigPanel.tsx
      RunConfirmModal.tsx
      WorkflowGraph.tsx
      WorkflowGraphNode.tsx
      WorkflowNode.tsx
      WorkflowRunSummary.tsx
```

| File/nhóm | Vai trò |
| --- | --- |
| `RunsPage.tsx` | Workspace full-screen của Runs, fixed header/actions, create-run flow |
| `catalog.ts` | Metadata presentation frontend: thứ tự, icon, accent, source options |
| `types.ts` | TypeScript contract cho node, field, composer state và run request |
| `state.ts` | Pure state logic: status, toggle rules, config merge, validation |
| `useWorkflowCatalog.ts` | Gọi `GET /admin/workflows/catalog`, map backend items sang UI nodes |
| `useWorkflowComposer.ts` | Orchestrate catalog, composer state và create run request |
| `WorkflowGraph.tsx` | Dựng React Flow nodes/edges từ backend catalog và edge labels |
| `WorkflowNode.tsx` | Custom graph node với trạng thái selected/available/blocked |
| `NodeConfigDrawer.tsx` | Drawer cấu hình nhanh cho các node đã chọn |
| `ConfigModal.tsx` | Modal cấu hình tập trung cho một node |
| `RunConfirmModal.tsx` | Modal xác nhận trước khi `POST /admin/runs` |
| `ConfigField.tsx` | Render text/number/select/checkbox/multi-select fields |

## Mục Tiêu UX

Trang Runs là màn hình vận hành pipeline, không phải màn hình nhập JSON. Admin cần
nhìn vào graph và biết ngay:

- node nào đã được chọn;
- node nào còn bị khóa vì thiếu dependency;
- node nào sẽ chạy trước/sau;
- config nào đang khác default;
- output chính sẽ nằm ở đâu;
- run sắp tạo có hợp lệ hay không.

Vì vậy UI tránh raw payload preview. Payload vẫn tồn tại trong state để gửi API,
nhưng người dùng thao tác qua graph, form và modal xác nhận. Điều này giảm khả năng
admin sửa nhầm key config hoặc gửi payload không khớp contract backend.

## Luồng UI

1. Admin mở `/admin/runs`.
2. `useWorkflowCatalog` gọi `adminApi.getWorkflowCatalog()`.
3. UI map backend `items` thành `WorkflowNodeDefinition`.
4. Metadata từ `catalog.ts` thêm icon, short title, accent và vị trí cố định.
5. `WorkflowGraph` render node và dependency edge.
6. Click node available để chọn.
7. Click node selected để bỏ chọn và bỏ luôn downstream node đã chọn.
8. Node blocked không chọn được.
9. Admin cấu hình node đã chọn bằng drawer/modal.
10. `Run workflow` validate request và mở `RunConfirmModal`.
11. Confirm sẽ gọi `adminApi.createRun("milestone_graph", config)`.
12. Trang hiển thị floating success action để mở run detail.

Trang này cố ý không hiển thị raw payload preview. Graph, form config và confirm
modal là UI vận hành chính.

## State Model

Composer state có các phần chính:

```text
nodes
selectedNodeIds
activeNodeId
configs
edgeLabels
runRequest
```

`selectedNodeIds` luôn được sort theo `workflowNodeOrder`, không theo thứ tự click.
Điều này giúp payload gửi backend ổn định và summary hiển thị đúng thứ tự chạy.

`configs` là map theo node id:

```ts
{
  m01_ingestion: {
    sources: ["cafef"],
    discover_download: true
  },
  m06_extraction: {
    retrieval_config: "metadata_aware_hybrid",
    max_contexts: 5
  }
}
```

Khi catalog load xong, mỗi node nhận config ban đầu từ `default_config` backend. Nếu
backend thêm field mới có default, UI sẽ tự nhận field đó mà không cần hard-code logic
mới trong frontend.

## Quy Ước Backend Catalog

Frontend không hard-code dependency hoặc config fields. Backend catalog là source of
truth:

```text
GET /admin/workflows/catalog
```

Shape frontend dùng:

```ts
type BackendCatalogResponse = {
  items: Array<{
    id: WorkflowNodeId;
    milestone: string;
    title: string;
    description: string;
    depends_on: WorkflowNodeId[];
    default_config: Record<string, unknown>;
    expected_artifacts: string[];
    fields: WorkflowFieldDefinition[];
  }>;
  edge_labels?: Record<string, string>;
};
```

Mapping:

```text
depends_on      -> dependsOn
default_config  -> defaultConfig
edge_labels     -> edgeLabels
```

Backend quyết định workflow contract. Frontend chỉ quyết định presentation: icon,
màu, short title và vị trí graph.

## Vì Sao Vẫn Có Presentation Metadata Ở Frontend

Backend catalog không nên chứa mọi chi tiết UI như icon, accent color hoặc tọa độ
graph. Những phần đó là presentation concern. Vì vậy frontend giữ:

```text
workflowNodeOrder
workflowNodePresentation
articleSourceOptions
nodePositions
```

Tuy nhiên frontend không tự quyết định node nào phụ thuộc node nào. Dependency luôn
đến từ backend `depends_on`. Nếu backend đổi dependency mà frontend chưa đổi vị trí
graph, UI vẫn validate đúng; chỉ layout có thể cần chỉnh lại để dễ nhìn.

## Graph Hiện Tại

```text
M00 Runtime
  -> M01 Ingestion
      -> M02 Labeling
          -> M03 RAG
              -> M04 Retrieval
                  -> M06 Extraction
                      -> M07 Verification
M04 Retrieval + M07 Verification
  -> M08 Evaluation
```

Không còn node M05 active trong composer.

| Node | Phụ thuộc |
| --- | --- |
| `m00_runtime` | none |
| `m01_ingestion` | `m00_runtime` |
| `m02_labeling` | `m01_ingestion` |
| `m03_rag` | `m01_ingestion`, `m02_labeling` |
| `m04_retrieval` | `m02_labeling`, `m03_rag` |
| `m06_extraction` | `m04_retrieval` |
| `m07_verification` | `m06_extraction` |
| `m08_evaluation` | `m04_retrieval`, `m07_verification` |

## Trạng Thái Node

`getNodeStatus` trả một trong ba trạng thái:

| Status | Điều kiện | UI behavior |
| --- | --- | --- |
| `selected` | Node id nằm trong `selectedNodeIds` | Card sáng, có check icon |
| `available` | Tất cả dependency đã selected | Card active/clickable |
| `blocked` | Thiếu ít nhất một dependency | Card xám có lock, click bị bỏ qua |

Trong code hiện tại dùng `blocked`, không dùng `locked`.

## Quy Tắc Dependency

Dependency có hai lớp:

1. Frontend chặn chọn node blocked để tránh UX gây nhầm.
2. Backend validate lại khi tạo run để đảm bảo contract không bị bypass.

Khi bỏ chọn một node, frontend phải bỏ mọi downstream node phụ thuộc trực tiếp hoặc
gián tiếp vào node đó. Đây là điểm quan trọng vì nếu chỉ bỏ node hiện tại, graph có
thể còn lại một run path không hợp lệ, ví dụ M06 selected nhưng M04 đã bị bỏ.

Ví dụ:

```text
Selected: M00, M01, M02, M03, M04, M06, M07
User bỏ M03
Remaining: M00, M01, M02
Removed: M03, M04, M06, M07
```

Logic này nằm trong `dependsOnNode`, có kiểm tra dependency bắc cầu.

## Toggle Rules

Chọn node:

```text
status === "available"
selectedNodeIds = sortWorkflowNodes([...selectedNodeIds, nodeId])
activeNodeId = nodeId
```

UI không tự chọn dependency. Admin phải chọn prerequisite trước để đường chạy rõ
ràng.

Bỏ chọn node:

```text
status === "selected"
remove nodeId
remove every selected node that transitively depends on nodeId
activeNodeId = last selected node || "m00_runtime"
```

Ví dụ bỏ M03 sẽ bỏ M04, M06, M07 và M08 nếu các node đó đang selected.

## Config Forms

Field type hiện hỗ trợ:

| Type | Control |
| --- | --- |
| `text` | Text input |
| `number` | Stepper kèm numeric input |
| `select` | Native select |
| `checkbox` | Toggle switch |
| `multi-select` | Pill button list |

`NodeConfigPanel` và `ConfigModal` ẩn field có `configurable === false`. Các field
này vẫn tồn tại trong state vì là một phần của backend contract.

Config ban đầu:

```ts
configs[node.id] = { ...node.defaultConfig };
```

## Render Field Config

`ConfigField.tsx` render theo `WorkflowFieldDefinition.type`:

| Type | Dữ liệu lưu trong config | Ghi chú |
| --- | --- | --- |
| `text` | string | Dùng cho path hoặc model name |
| `number` | number | Có `min`, `max`, `step` từ backend |
| `select` | string | Option lấy từ backend catalog |
| `checkbox` | boolean | Dùng cho các switch như `sync_postgres` |
| `multi-select` | string[] | Dùng cho source list |

Không nên thêm logic riêng cho từng node trong `ConfigField`. Nếu một field cần giải
thích thêm, backend nên cung cấp `description`. Nếu một field không nên sửa từ UI,
backend đặt `configurable=false`.

## Ghi Chú Config Theo Node

### M01 Ingestion

- `discover_download` mặc định `true`.
- `sources` là multi-select dùng riêng cho discovery/download.
- `max_articles` là số bài download tối đa khi discovery/download bật.
- `max_discovered_urls` giới hạn candidate URLs trước khi download.
- `min_text_chars` là số ký tự sau normalize, không phải số từ.
- `reset_html_snapshots` xóa local `*.html` và HTML manifest đang chọn trước khi
  chạy M01; không xóa DB data hoặc downstream artifacts.
- `articles_path`, `input_html_dir`, `html_manifest_path` là field không configurable
  để UI biết target local.

Frontend chặn M01 nếu `discover_download=true` nhưng `sources=[]`.

M01 có điểm dễ nhầm: `sources` chỉ điều khiển discovery/download. Nó không filter lại
toàn bộ HTML local khi parse. Nếu trong `data/raw/html` có file từ source khác, M01
vẫn parse file đó. Đây là chủ ý để không làm mất local snapshots khi admin chỉ muốn
giới hạn nguồn crawl mới.

### M02 Labeling

Normal mode bật cả ba switch:

- `generate_prompts`: tạo prompt records từ clean articles.
- `run_teacher`: gọi teacher LLM cho prompt records.
- `validate_labels`: validate teacher output thành gold/rejected labels.

`max_articles` là số prompt/article records được chọn để label. Nó không bao gồm
retry. Nếu `max_articles=25`, run chọn tối đa 25 prompt records; `teacher_max_retries`
điều khiển số lần retry cho mỗi prompt đã chọn.

`strict_validation` mặc định `true`, nghĩa là chỉ label `PASS` mới vào gold set.

`generate_prompts`, `run_teacher`, `validate_labels` không phải những bước optional
cho normal run. Chúng được expose để resume/debug. Admin bình thường nên để cả ba bật,
vì M02 là bước tạo gold labels chính cho M03/M04/M08.

### M03 RAG

M03 là bước offline preparation. Nó build chunk artifacts, retrieval embeddings,
BM25/vector artifacts, gold-derived pattern records và `chunk_patterns.jsonl`.
Pattern refs được gắn vào chunks; workflow hiện tại không dùng vector index riêng cho
patterns.

### M04 Retrieval

M04 chạy online retrieval theo từng article và ghi
`data/retrieval/online_contexts.jsonl`. Nó cũng có thể sync retrieval runs và
contexts vào PostgreSQL.

`retrieval_config` chọn recipe tính điểm/rerank dùng để tạo context pack M04. Nó không
có nghĩa là chọn một nguồn retrieve đơn lẻ rồi bỏ các signal khác. Các option hiện có:

- `bm25_only`
- `dense_only`
- `hybrid`
- `metadata_aware_hybrid`
- `rule_aware_rerank`
- `llm_reasoning_rerank`
- `multi_event_aware_hybrid`

`multi_event_aware_hybrid` vẫn là recipe hybrid: nó kết hợp dense, BM25, metadata,
rule score, event-intent queries và coverage/MMR. Đây không phải một chế độ blend riêng
của M06. Nếu muốn M06 dùng context multi-event, admin phải chạy M04 với recipe này
trước.

Việc UI bắt chọn một `retrieval_config` ở M04 là để tạo artifact deterministic cho M06:
mỗi article/config có một context record rõ ràng. Luồng so sánh nhiều recipe vẫn là
command `finevent.retrieval compare`; graph run production không trộn nhiều output
retrieval trong cùng một extraction prompt. Chi tiết:
[multi-event-aware retrieval](../workflows/retrieval/multi-event-aware-retrieval.md).

`llm_rerank_mode` là bước rerank listwise cuối cùng của M04. Mặc định `student_env`,
tức là dùng student model cấu hình trong `.env` để đọc pool đã qua scoring/strategy
selection. Với `multi_event_aware_hybrid`, coverage/MMR vẫn chạy trước để giữ đa dạng
event; backend chỉ nới pool trước LLM rộng hơn `max_contexts`, tối thiểu theo
`llm_rerank_top_n`, rồi LLM trả về thứ tự mới. Prompt không đưa nguyên toàn bộ bài báo
gốc của mỗi chunk, chỉ đưa title, source, published date, document preview, chunk text
ngắn, pattern refs và score breakdown.
Khi admin chạy smoke test không có LLM endpoint, có thể đổi mode sang `deterministic`
hoặc `off`.

### M06 Extraction

M06 đọc M04 contexts từ `retrieval_results_path`. Nó chọn context record khớp
`article_id` và `retrieval_config`, rồi giới hạn số context đưa vào prompt bằng
`max_contexts`.

M06 không retrieve chunks và không fetch pattern records riêng. Prompt nhận
`matched_patterns` từ `pattern_refs` gắn trên các retrieved chunks.

## Validation Trước Khi Tạo Run

Frontend tạo `runRequest` mỗi khi selected nodes hoặc configs thay đổi. Nếu request
không hợp lệ, `runRequest.ok=false` và UI hiển thị lý do.

Các rule hiện có:

- phải chọn ít nhất một node;
- mọi dependency của selected node phải nằm trong `selectedNodeIds`;
- M01 `max_articles` phải là số nguyên từ 1;
- M01 `discover_download=true` phải có ít nhất một source;
- M06 `limit` phải là số nguyên từ 1;
- M06 `offset` phải là số nguyên không âm;
- M06 `max_contexts` phải là số nguyên từ 1;
- M06 `output_path` không được rỗng.

Không nên xem frontend validation là security boundary. Backend vẫn validate lại mọi
request. Frontend validation chỉ giúp admin thấy lỗi sớm.

## Build Run Request

`buildWorkflowRunRequest` trả:

```ts
{
  ok: true,
  workflowName: "milestone_graph",
  selectedNodes,
  config
}
```

Config shape:

```json
{
  "selected_nodes": ["m00_runtime", "m01_ingestion", "m02_labeling"],
  "node_configs": {
    "m01_ingestion": {
      "sources": ["cafef"],
      "discover_download": true
    }
  },
  "sources": ["cafef"],
  "discover_download": true
}
```

Backend command builder ưu tiên `node_configs.<node_id>` hơn flattened keys.

## Run Confirmation

`RunConfirmModal` hiển thị danh sách node sẽ chạy theo thứ tự registry, không hiển thị
raw JSON. Modal này giúp admin kiểm tra lại workflow path trước khi tạo run.

Nội dung confirm nên trả lời được:

- run sẽ chạy những milestone nào;
- M07 có được bật trong M06 không;
- output chính nằm ở đâu;
- các config quan trọng như source, max articles, retrieval strategy đã đúng chưa.

Nếu sau này cần hiển thị diff config so với default, nên thêm vào modal theo dạng
human-readable table, không đưa raw payload trở lại làm UI chính.

## Validation Trước Khi Chạy

Frontend kiểm tra:

- phải chọn ít nhất một node;
- mọi dependency của selected node phải được chọn;
- M01 `max_articles` là số nguyên từ 1;
- M01 `discover_download=true` phải có ít nhất một source;
- M06 `limit` là số nguyên từ 1;
- M06 `offset` là số nguyên không âm;
- M06 `max_contexts` là số nguyên từ 1;
- M06 `output_path` không được rỗng.

Backend vẫn validate lại dependency và workflow. Frontend validation chỉ để UX tốt
hơn.

## Design Notes

- Graph là full-screen operational workspace, không phải form card truyền thống.
- Header và run/settings actions fixed để luôn truy cập được.
- Drawer dùng cho config nhanh nhiều node.
- Modal dùng cho config tập trung từng node và xác nhận run.
- Tooltip render qua portal để không bị clip bởi React Flow canvas.
- Run history không nhét vào graph page; run vừa tạo đi qua floating success action và run detail page.

## Failure Và Loading State

Các trạng thái cần giữ rõ:

| Trạng thái | UI mong muốn |
| --- | --- |
| Catalog loading | Hiển thị loading state, không render graph rỗng |
| Catalog error | Hiển thị lỗi và nút retry |
| Node blocked | Card xám, lock icon, tooltip giải thích thiếu dependency |
| Config invalid | Disable create run hoặc hiển thị warning rõ |
| Create run pending | Disable confirm button để tránh double submit |
| Create run success | Floating action mở run detail |

Nếu backend catalog thiếu một node presentation trong frontend, UI nên vẫn render node
với fallback title/icon thay vì crash. Tuy nhiên node mới đúng chuẩn vẫn cần cập nhật
`workflowNodePresentation` để graph dễ scan.

## Cách Thêm Node

1. Backend thêm `WorkflowNodeSpec` mới và expose qua catalog.
2. Frontend thêm id vào `WorkflowNodeId`.
3. Thêm id vào `workflowNodeOrder`.
4. Thêm icon, `shortTitle`, `accent` vào `workflowNodePresentation`.
5. Thêm fixed position trong `WorkflowGraph.tsx` nếu cần.
6. Đảm bảo backend `depends_on`, `default_config`, `fields` đủ để UI render.
7. Cập nhật tests và docs.

Check:

```powershell
pnpm check-types
pnpm lint
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_admin_api.py
```
