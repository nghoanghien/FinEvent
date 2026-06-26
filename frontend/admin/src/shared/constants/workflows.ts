import type { WorkflowPreset } from "../types";

export const workflowPresets: WorkflowPreset[] = [
  {
    id: "student_batch_extraction",
    title: "Student Batch Extraction",
    description: "Chạy model 8B trên tập bài báo đã xử lý, có thể sync output về PostgreSQL.",
    accent: "sky",
    defaultConfig: {
      articles_path: "data/processed/articles_clean.jsonl",
      output_path: "data/extraction/student_predictions.jsonl",
      student_provider: "env",
      retrieval_query_embedding_provider: "langchain_openai",
      pattern_query_embedding_provider: "langchain_openai",
      limit: 10,
      offset: 0,
      sync_postgres: true,
    },
  },
  {
    id: "evaluation",
    title: "Final Evaluation And Reports",
    description: "Tạo metric, bảng lỗi, biểu đồ học thuật và report phục vụ báo cáo đồ án.",
    accent: "emerald",
    defaultConfig: {
      gold_path: "data/labels/events_gold.jsonl",
      runs_dir: "runs/extraction",
      evaluation_output_dir: "reports/evaluation",
      skip_academic_figures: false,
    },
  },
  {
    id: "student_batch_with_evaluation",
    title: "Extraction + Evaluation",
    description: "Chạy extraction batch rồi đánh giá ngay trên predictions vừa sinh.",
    accent: "amber",
    defaultConfig: {
      articles_path: "data/processed/articles_clean.jsonl",
      output_path: "data/extraction/student_predictions.jsonl",
      student_provider: "env",
      retrieval_query_embedding_provider: "langchain_openai",
      pattern_query_embedding_provider: "langchain_openai",
      gold_path: "data/labels/events_gold.jsonl",
      evaluation_output_dir: "reports/evaluation",
      limit: 10,
      offset: 0,
      sync_postgres: true,
    },
  },
];

export function workflowTitle(id?: string) {
  if (id === "milestone_graph") return "Milestone Graph";
  return workflowPresets.find((preset) => preset.id === id)?.title || id || "Workflow";
}
