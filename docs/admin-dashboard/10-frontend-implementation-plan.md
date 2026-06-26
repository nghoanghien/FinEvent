# 10 - Frontend Implementation Plan

## Implementation Update - Runs Page

Trang `/admin/runs` hiện đã chuyển sang Milestone Graph Composer. Không còn `WorkflowRunner` dạng preset card + JSON textarea. Implementation hiện dùng `@xyflow/react` để render graph, `framer-motion` cho drawer/modal, `useWorkflowCatalog` để hydrate catalog từ backend và `useWorkflowComposer` để quản lý selected nodes/config/run request.

## Tech Stack

| Thành phần | Công nghệ | Vai trò |
| --- | --- | --- |
| Framework | Next.js App Router | Routing và page layout |
| Language | TypeScript | Type-safe UI/API models |
| Styling | Tailwind CSS | Layout và utility classes |
| Components | shadcn/ui | Button, table, tabs, dialog, sheet, badge |
| Data fetching | TanStack Query | Fetch/cache/refetch API |
| Workflow graph | @xyflow/react | Render node/edge graph M00-M08 |
| Motion/modal | framer-motion | Drawer, config modal, confirm modal |
| Tables | TanStack Table | Sort/filter/pagination |
| Realtime | EventSource/SSE | Live logs |
| Charts | Recharts hoặc Tremor | Metrics cards/charts |
| Markdown | react-markdown | Render `.md` reports |
| JSON viewer | react-json-view-lite hoặc custom | Raw JSON/debug |

## Folder Structure

```text
frontend/
  app/
    admin/
      page.tsx
      runs/
        page.tsx
        [runId]/
          page.tsx
      database/
        page.tsx
      reports/
        page.tsx
      outputs/
        page.tsx
      settings/
        page.tsx
  components/
    admin/
      AppShell.tsx
      Sidebar.tsx
      StatusBadge.tsx
      MetricCard.tsx
      WorkflowGraph.tsx
      RunTimeline.tsx
      LiveLogViewer.tsx
      ArtifactList.tsx
      DatabaseTable.tsx
      ReportViewer.tsx
      StructuredOutputViewer.tsx
      EventTable.tsx
      VerificationPanel.tsx
  lib/
    api.ts
    sse.ts
    types.ts
    format.ts
```

## Routes

### `/admin`

Overview dashboard.

Content:

- health cards;
- latest metrics;
- latest run;
- quick action buttons;
- report index link.

### `/admin/runs`

Milestone graph workflow composer.

Content:

- React Flow graph M00-M08;
- fixed PageHeader và Run/Settings actions;
- node tooltip/settings;
- config drawer;
- run confirmation modal;
- floating action mở run vừa tạo.

### `/admin/runs/[runId]`

Run detail.

Tabs:

- Timeline;
- Live Logs;
- Artifacts;
- Metrics;
- Errors;
- Raw.

### `/admin/database`

Database browser.

Tabs:

- articles;
- chunks;
- labels;
- patterns;
- extraction runs;
- tickers.

### `/admin/reports`

Report viewer.

Left list + main viewer.

### `/admin/outputs`

Structured output viewer.

Search by article_id/run_id.

### `/admin/settings`

Health and runtime configuration.

## Component Requirements

### Workflow Composer

Files:

- `workflow-composer/hooks/useWorkflowCatalog.ts`;
- `workflow-composer/hooks/useWorkflowComposer.ts`;
- `workflow-composer/components/WorkflowGraph.tsx`;
- `workflow-composer/components/WorkflowNode.tsx`;
- `workflow-composer/components/NodeConfigDrawer.tsx`;
- `workflow-composer/components/ConfigModal.tsx`;
- `workflow-composer/components/RunConfirmModal.tsx`.

Behavior:

- fetch backend catalog from `GET /admin/workflows/catalog`;
- render node/edge graph;
- block nodes whose dependencies are missing;
- click selected node again to turn it off;
- turn off downstream dependent nodes automatically;
- build run request with `selected_nodes`, `node_configs` and merged flat config;
- confirm before calling `POST /admin/runs`.

### LiveLogViewer

Props:

- run_id;
- optional step filter.

Behavior:

- connect SSE;
- append lines;
- auto-scroll;
- pause/resume;
- search/filter;
- reconnect on network drop.

### DatabaseTable

Props:

- entity name;
- columns;
- filters.

Behavior:

- fetch paginated rows;
- sort/filter;
- open detail drawer;
- copy IDs.

### ReportViewer

Props:

- report path.

Behavior:

- choose renderer by kind;
- Markdown render;
- CSV table;
- JSONL list/detail;
- raw fallback.

### StructuredOutputViewer

Props:

- run_id or article_id.

Behavior:

- show article summary;
- show event table;
- event detail drawer;
- evidence highlight;
- verification panel;
- raw JSON tab.

## Visual Design

Dashboard nên có cảm giác công cụ vận hành:

- dense but readable;
- ít hero/marketing;
- sidebar rõ;
- table nhiều thông tin;
- badge status nhất quán;
- typography nhỏ vừa phải;
- cards dùng cho metric/repeated items, không lồng card quá nhiều.

Status badges:

| Status | Color |
| --- | --- |
| success | green |
| running | blue |
| failed | red |
| warning | amber |
| queued | gray |
| canceled | yellow |

## Loading And Empty States

Mỗi màn hình cần:

- loading skeleton;
- empty state có hành động tiếp theo;
- error state có message rõ;
- retry button.

Ví dụ Reports empty:

> Chưa có evaluation report. Hãy chạy workflow `Final Evaluation And Reports`.

## Frontend Không Được Làm

- Không chứa logic NLP.
- Không tự gọi model API.
- Không đọc `.env`.
- Không truy cập DB trực tiếp.
- Không parse vector lớn ở client.
- Không tự sửa artifact file.
