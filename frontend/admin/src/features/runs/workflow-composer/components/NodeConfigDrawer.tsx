"use client";

import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { NodeConfigPanel } from "./NodeConfigPanel";
import type { WorkflowComposerState, WorkflowNodeDefinition, WorkflowNodeId, WorkflowRunRequest } from "../types";

type NodeConfigDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
  runRequest: WorkflowRunRequest;
  composerState: WorkflowComposerState;
  nodeById: Record<string, WorkflowNodeDefinition>;
  onChange: (nodeId: WorkflowNodeId, key: string, value: any) => void;
  onSetActiveNode: (nodeId: WorkflowNodeId) => void;
};

export function NodeConfigDrawer({
  isOpen,
  onClose,
  runRequest,
  composerState,
  nodeById,
  onChange,
  onSetActiveNode,
}: NodeConfigDrawerProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop click to dismiss */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[80] bg-slate-900/10 backdrop-blur-[2px] !mt-0"
          />
          {/* Sliding Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed bottom-0 right-0 top-0 z-[90] flex h-full w-full max-w-md flex-col rounded-l-[32px] border-l border-slate-200 bg-white/95 shadow-2xl backdrop-blur-md !mt-0"
          >
            {/* Header inside drawer */}
            <div className="flex items-center justify-between border-b border-slate-100 p-6">
              <div>
                <h3 className="mt-0.5 font-anton text-2xl font-black uppercase text-gray-900">
                  Cấu hình Node
                </h3>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Scrollable content inside drawer */}
            <div className="flex-1 overflow-y-auto p-6">
              {!runRequest.ok && runRequest.message ? (
                <div className="mb-6 rounded-2xl bg-rose-50 border border-rose-100 p-4 text-xs font-bold text-rose-600 animate-[fadeInUp_0.2s_ease-out]">
                  {runRequest.message}
                </div>
              ) : null}

              <NodeConfigPanel
                state={composerState}
                nodeById={nodeById}
                onChange={onChange}
                onSetActiveNode={onSetActiveNode}
                flat={true}
              />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
