import {
  BarChart3,
  BookOpenCheck,
  DatabaseZap,
  FileSearch,
  GitBranch,
  HardDrive,
  Layers3,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { WorkflowNodeId } from "./types";

export const workflowNodeOrder: WorkflowNodeId[] = [
  "m00_runtime",
  "m01_ingestion",
  "m02_labeling",
  "m03_rag",
  "m04_retrieval",
  "m05_patterns",
  "m06_extraction",
  "m07_verification",
  "m08_evaluation",
];

export const articleSourceOptions = [
  { value: "cafef", label: "CafeF" },
  { value: "vietstock", label: "Vietstock" },
  { value: "tinnhanhchungkhoan", label: "Tin nhanh CK" },
  { value: "nhadautu", label: "Nhà đầu tư" },
];

export const workflowNodePresentation: Record<
  WorkflowNodeId,
  {
    shortTitle: string;
    accent: "sky" | "emerald" | "amber";
    icon: any;
  }
> = {
  m00_runtime: {
    shortTitle: "Runtime",
    accent: "sky",
    icon: HardDrive,
  },
  m01_ingestion: {
    shortTitle: "Ingest",
    accent: "sky",
    icon: DatabaseZap,
  },
  m02_labeling: {
    shortTitle: "Label",
    accent: "amber",
    icon: BookOpenCheck,
  },
  m03_rag: {
    shortTitle: "RAG",
    accent: "emerald",
    icon: Layers3,
  },
  m04_retrieval: {
    shortTitle: "Retrieve",
    accent: "emerald",
    icon: FileSearch,
  },
  m05_patterns: {
    shortTitle: "Patterns",
    accent: "emerald",
    icon: GitBranch,
  },
  m06_extraction: {
    shortTitle: "Extract",
    accent: "sky",
    icon: Sparkles,
  },
  m07_verification: {
    shortTitle: "Verify",
    accent: "amber",
    icon: ShieldCheck,
  },
  m08_evaluation: {
    shortTitle: "Evaluate",
    accent: "emerald",
    icon: BarChart3,
  },
};
