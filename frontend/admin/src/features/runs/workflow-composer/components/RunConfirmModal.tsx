"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Play, GitBranch } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { WorkflowNodeDefinition, WorkflowNodeId } from "../types";
import { workflowTitle } from "@/shared/constants/workflows";

type RunConfirmModalProps = {
  isOpen: boolean;
  workflowName: string;
  selectedNodeIds: WorkflowNodeId[];
  nodeById: Record<string, WorkflowNodeDefinition>;
  isPending: boolean;
  onConfirm: () => void;
  onClose: () => void;
};

export function RunConfirmModal({
  isOpen,
  workflowName,
  selectedNodeIds,
  nodeById,
  isPending,
  onConfirm,
  onClose,
}: RunConfirmModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Close modal on Escape key press
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="absolute inset-0 bg-ink-900/60 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="relative z-10 w-full max-w-md rounded-[32px] border border-white/40 bg-white/90 p-6 shadow-2xl backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-4 border-b border-gray-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-lime-50 text-lime-600 border border-lime-100">
                  <GitBranch className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-xs font-black uppercase text-gray-400">
                    Xác nhận khởi chạy
                  </span>
                  <h3 className="mt-0.5 font-anton text-2xl font-black uppercase text-gray-900">
                    Chạy Workflow Pipeline
                  </h3>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="focus-ring flex h-8 w-8 items-center justify-center rounded-full border border-gray-100 hover:bg-gray-50 text-gray-400 hover:text-gray-700 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Content */}
            <div className="mt-5 space-y-4">
              <p className="text-sm font-semibold text-gray-600">
                Bạn có chắc chắn muốn khởi chạy workflow sau không?
              </p>
              
              <div className="rounded-2xl border border-gray-100 bg-gray-50/50 p-4">
                <div className="text-xs font-black uppercase text-gray-400">Workflow</div>
                <div className="text-sm font-bold text-gray-800 mt-0.5">
                  {workflowTitle(workflowName)}
                </div>
                
                <div className="text-xs font-black uppercase text-gray-400 mt-3">Các Node được chạy ({selectedNodeIds.length})</div>
                <div className="mt-1 flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto pr-1">
                  {selectedNodeIds.map((nodeId) => {
                    const node = nodeById[nodeId];
                    if (!node) return null;
                    return (
                      <span
                        key={nodeId}
                        className="inline-flex items-center gap-1 rounded-full bg-lime-50 border border-lime-100 px-2 py-0.5 text-[10px] font-bold text-lime-800"
                      >
                        <span className="text-[9px] font-black uppercase text-lime-500">{node.milestone}</span>
                        {node.shortTitle}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center justify-end gap-3 border-t border-gray-100 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="focus-ring inline-flex h-11 items-center justify-center rounded-full border border-gray-200 bg-white px-6 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition active:scale-95"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                disabled={isPending}
                onClick={onConfirm}
                className="focus-ring eatzy-primary-button h-11 px-6 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                {isPending ? "Đang chạy..." : "Khởi chạy"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
