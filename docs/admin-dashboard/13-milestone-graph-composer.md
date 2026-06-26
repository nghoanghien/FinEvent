# 13 - Milestone Graph Composer

## Mục Tiêu

Milestone Graph Composer là implementation hiện tại của trang `/admin/runs`. Trang này không còn dùng preset workflow + textarea JSON. UI hydrate catalog từ backend, dựng graph M00-M08 bằng React Flow, cho admin bật/tắt node theo dependency, cấu hình node bằng drawer/modal, xác nhận trước khi tạo run `milestone_graph`.

Mục tiêu vận hành:

- Admin chỉ chọn được node hợp lệ theo dependency.
- Node đang chọn sáng lên; node thiếu dependency bị khóa/xám.
- Click lại node đã chọn sẽ tắt node đó.
- Tắt một node sẽ tắt luôn downstream node phụ thuộc.
- Config chạy workflow nằm trong form rõ ràng, không hiển thị raw payload review.
- Backend vẫn validate lại toàn bộ dependency khi nhận `POST /admin/runs`.

## Code Map

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

Dependencies frontend mới:

```json
{
  "@xyflow/react": "...",
  "framer-motion": "..."
}
```

Vai trò từng nhóm:

| File/nhóm | Vai trò |
| --- | --- |
| `RunsPage.tsx` | Layout trang Runs, fixed header/actions, gọi composer hook, tạo run |
| `catalog.ts` | Presentation metadata frontend: node order, icon, short title, accent, source options |
| `types.ts` | Type contract cho node, field, composer state, run request |
| `state.ts` | Pure state logic: status, toggle, downstream removal, config merge, validation |
| `useWorkflowCatalog.ts` | Gọi `GET /admin/workflows/catalog`, map backend item sang UI node, sort theo `workflowNodeOrder` |
| `useWorkflowComposer.ts` | Orchestrate catalog + composer state + run request |
| `WorkflowGraph.tsx` | Dựng React Flow nodes/edges từ backend catalog và `edge_labels` |
| `WorkflowNode.tsx` | Custom React Flow node: selected/available/blocked state, tooltip, settings button |
| `NodeConfigDrawer.tsx` | Drawer cấu hình các node đã chọn |
| `ConfigModal.tsx` | Modal cấu hình node khi bấm settings trên node |
| `RunConfirmModal.tsx` | Modal xác nhận trước khi gọi create run |
| `ConfigField.tsx` | Render field text/number/select/checkbox/multi-select |

`WorkflowRunSummary.tsx` vẫn được export như reusable component, nhưng flow chính hiện tại dùng top action button + `RunConfirmModal`.

## Luồng UI Hiện Tại

1. Admin mở `/admin/runs`.
2. `useWorkflowCatalog` gọi `adminApi.getWorkflowCatalog()`.
3. UI map `items` từ backend thành `WorkflowNodeDefinition`, gắn thêm icon/short title/accent từ `catalog.ts`.
4. `WorkflowGraph` dựng React Flow graph bằng node positions cố định và edge labels từ backend.
5. Admin click node:
   - node `blocked` không thay đổi;
   - node `available` được thêm vào `selectedNodeIds`;
   - node `selected` bị tắt, kéo theo downstream node phụ thuộc.
6. Admin mở settings drawer để chỉnh config của các node đã chọn.
7. Admin có thể bấm settings trên từng selected node để mở modal config node.
8. Admin bấm `Run workflow`.
9. Nếu `runRequest.ok=false`, UI hiển thị warning message.
10. Nếu hợp lệ, UI mở `RunConfirmModal`.
11. Xác nhận sẽ gọi `POST /admin/runs` với `workflowName = "milestone_graph"`.
12. Khi tạo run thành công, UI hiện nút floating để mở run detail.

Trang Runs hiện không còn bảng run history trong cùng màn hình graph. Run vừa tạo được mở qua floating success action, còn run detail vẫn ở `/admin/runs/{run_id}`.

## Backend Catalog Contract

Frontend không hard-code dependency hay config fields. Nguồn dữ liệu chính là:

```text
GET /admin/workflows/catalog
```

Shape được dùng trong `useWorkflowCatalog`:

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

Frontend map:

```text
depends_on      -> dependsOn
default_config  -> defaultConfig
edge_labels     -> edgeLabels
```

Presentation metadata vẫn ở frontend:

```text
workflowNodeOrder
workflowNodePresentation
articleSourceOptions
```

Lý do: backend quyết định workflow contract, frontend quyết định icon, vị trí, màu và tên ngắn phục vụ UI.

## Trạng Thái Node

`getNodeStatus` trả một trong ba trạng thái:

| Trạng thái | Điều kiện | UI |
| --- | --- | --- |
| `selected` | Node nằm trong `selectedNodeIds` | Card sáng, check icon, edge highlight nếu node kế cận cũng selected |
| `available` | Tất cả `dependsOn` đã selected | Card active/clickable |
| `blocked` | Thiếu ít nhất một dependency | Card xám, lock icon, click không có tác dụng |

Tên trạng thái hiện tại trong code là `blocked`, không phải `locked`.

## Toggle Rules

### Bật node

```text
status === "available"
selectedNodeIds = sortWorkflowNodes([...selectedNodeIds, nodeId])
activeNodeId = nodeId
```

UI không tự bật dependency. Admin phải chọn dependency trước để thấy đường chạy rõ ràng.

### Tắt node

```text
status === "selected"
remove nodeId
remove every selected node that transitively depends on nodeId
activeNodeId = last remaining selected node || "m00_runtime"
```

Logic downstream nằm trong `dependsOnNode`, có kiểm tra dependency bắc cầu. Ví dụ tắt M03 sẽ tắt M04, M05, M06, M07, M08 nếu các node đó đang selected.

## Graph Hiện Tại

```text
M00 Runtime
  -> M01 Ingestion
      -> M02 Labeling
          -> M04 Retrieval
          -> M05 Patterns
      -> M03 RAG
          -> M04 Retrieval
          -> M05 Patterns
          -> M06 Extraction
              -> M07 Verification
M04 Retrieval + M07 Verification
  -> M08 Evaluation
```

Dependency chi tiết:

| Node | Phụ thuộc |
| --- | --- |
| `m00_runtime` | none |
| `m01_ingestion` | `m00_runtime` |
| `m02_labeling` | `m01_ingestion` |
| `m03_rag` | `m01_ingestion` |
| `m04_retrieval` | `m02_labeling`, `m03_rag` |
| `m05_patterns` | `m02_labeling`, `m03_rag` |
| `m06_extraction` | `m03_rag`, `m05_patterns` |
| `m07_verification` | `m06_extraction` |
| `m08_evaluation` | `m04_retrieval`, `m07_verification` |

## React Flow Rendering

`WorkflowGraph.tsx` dùng `ReactFlowProvider` và custom node type:

```text
nodeTypes = { workflowNode: WorkflowNode }
```

Node positions đang cố định theo milestone để graph dễ scan:

```text
M00 -> M01 -> M02/M03 -> M04/M05 -> M06 -> M07 -> M08
```

Edges được tạo từ `node.dependsOn`. Edge được highlight khi cả source và target đều selected. Backend `edge_labels` cung cấp label như `Clean Articles`, `RAG Index`, `Verified Events`.

## Config Forms

Field type hiện có:

| Type | Control |
| --- | --- |
| `text` | Text input |
| `number` | Stepper + numeric input |
| `select` | Native select |
| `checkbox` | Toggle switch |
| `multi-select` | Pill button list |

`NodeConfigPanel` trong drawer chỉ hiển thị field có `configurable !== false`.

`ConfigModal` mở từ settings button trên selected node và render fields của node đang chọn. Settings button chỉ xuất hiện nếu node có ít nhất một field configurable.

Config state ban đầu lấy từ `defaultConfig` của backend catalog:

```ts
configs[node.id] = { ...node.defaultConfig };
```

## Build Run Request

`buildWorkflowRunRequest` tạo payload nội bộ:

```ts
{
  ok: true,
  workflowName: "milestone_graph",
  selectedNodes,
  config
}
```

`config` có hai phần:

```json
{
  "selected_nodes": ["m00_runtime", "m01_ingestion", "m06_extraction"],
  "node_configs": {
    "m06_extraction": {
      "limit": 10,
      "sources": ["cafef"],
      "retrieval_config": "multi_event_aware_hybrid",
      "max_contexts": 10,
      "pattern_count": 4
    }
  },
  "limit": 10,
  "sources": ["cafef"],
  "retrieval_config": "multi_event_aware_hybrid",
  "max_contexts": 10,
  "pattern_count": 4
}
```

Phần config phẳng là phần backend đang dùng để build command. `node_configs` giữ lại cấu trúc theo node để debug/trace và có thể dùng cho extension sau này.

M06 expose `retrieval_config`, `max_contexts` và `pattern_count` từ backend catalog. Strategy
`multi_event_aware_hybrid` được mô tả tại
[`docs/workflows/retrieval/multi-event-aware-retrieval.md`](../workflows/retrieval/multi-event-aware-retrieval.md).

Trước khi `ok=true`, frontend validate:

- phải chọn ít nhất một node;
- mọi dependency của selected node phải nằm trong `selectedNodeIds`;
- M01 `max_articles` phải là số nguyên từ 1;
- M06 `limit` phải là số nguyên từ 1;
- M06 `offset` phải là số nguyên không âm;
- M06 `max_contexts` phải là số nguyên từ 1;
- M06 `pattern_count` phải là số nguyên từ 1;
- M06 `output_path` không được rỗng.

## Run Confirmation

Trang Runs không gọi API ngay khi bấm `Run workflow`. Flow hiện tại:

```text
Run workflow button
  -> validate runRequest
  -> open RunConfirmModal
  -> confirm
  -> createRun.mutate({ workflowName, config })
```

`RunConfirmModal` hiển thị workflow title và danh sách node sẽ chạy. UI không hiển thị raw JSON payload.

## API Client

Các API liên quan nằm trong `frontend/admin/src/shared/utils/api.ts`:

```ts
adminApi.getWorkflowCatalog()
adminApi.createRun(workflow_name, config)
adminApi.getRun(runId)
adminApi.logs(runId, query)
adminApi.cancelRun(runId)
```

`createRun` vẫn gửi snake_case contract cho backend:

```json
{
  "workflow_name": "milestone_graph",
  "config": {}
}
```

## Design/UX Notes

- Màn hình graph là full-screen workspace, không phải form/card truyền thống.
- Header và Run/Settings actions được fixed để luôn truy cập được.
- Drawer dùng cho config nhanh nhiều node.
- Modal dùng cho config tập trung từng node và xác nhận chạy workflow.
- Tooltip mô tả node render qua portal để không bị clip trong React Flow canvas.
- Không dùng raw payload preview vì UI đã có graph, form và confirm modal.
- Nếu catalog đang loading, trang hiện loading state thay vì render graph rỗng.

## Cách Thêm Node Mới

1. Backend thêm `WorkflowNodeSpec` và expose qua catalog.
2. Frontend thêm id vào `WorkflowNodeId`.
3. Thêm id vào `workflowNodeOrder`.
4. Thêm icon, `shortTitle`, `accent` vào `workflowNodePresentation`.
5. Nếu cần vị trí graph cố định, thêm vào `nodePositions` trong `WorkflowGraph.tsx`.
6. Đảm bảo `depends_on`, `default_config`, `fields` từ backend đủ để UI render.
7. Cập nhật docs backend API và docs frontend feature.

Checklist frontend:

```powershell
docker compose exec -T frontend pnpm lint
docker compose exec -T frontend pnpm check-types
```

Checklist backend:

```powershell
C:\Users\OWNER\miniconda3\envs\deep-learning-project\python.exe -m pytest tests/test_admin_api.py
```

## Acceptance Criteria

- Graph hydrate từ `GET /admin/workflows/catalog`.
- Node blocked không bật được.
- Click node selected lần nữa sẽ tắt node đó.
- Tắt node cha sẽ tắt downstream node phụ thuộc theo dependency bắc cầu.
- Drawer chỉ hiển thị config của selected configurable nodes.
- Run button mở confirm modal trước khi tạo run.
- UI gửi `workflowName: "milestone_graph"` và config gồm `selected_nodes`, `node_configs`, plus config phẳng.
- Backend vẫn reject request thiếu dependency dù request không đi qua UI.
