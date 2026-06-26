"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ConfigField } from "./ConfigField";
import type { WorkflowNodeDefinition } from "../types";

type ConfigModalProps = {
  isOpen: boolean;
  node: WorkflowNodeDefinition | null;
  configs: Record<string, any> | undefined;
  onChange: (key: string, value: any) => void;
  onClose: () => void;
};

export function ConfigModal({ isOpen, node, configs = {}, onChange, onClose }: ConfigModalProps) {
  const [mounted, setMounted] = useState(false);
  const [activeNode, setActiveNode] = useState<WorkflowNodeDefinition | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  useEffect(() => {
    if (node) {
      setActiveNode(node);
    }
  }, [node]);

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
      {isOpen && activeNode && (
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
            className="relative z-10 w-full max-w-lg rounded-[32px] border border-white/40 bg-white/90 p-6 shadow-2xl backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-4 border-b border-gray-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-lime-50 text-primary border border-lime-100">
                  <Settings className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-xs font-black uppercase text-gray-400">
                    CẤU HÌNH {activeNode.milestone}
                  </span>
                  <h3 className="mt-0.5 font-anton text-2xl font-black uppercase text-gray-900">
                    {activeNode.title}
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
            <div className="mt-5 max-h-[60vh] overflow-y-auto pr-1 space-y-4">
              <p className="text-sm font-semibold leading-relaxed text-ink-700">
                {activeNode.description}
              </p>

              {activeNode.fields && activeNode.fields.length > 0 ? (
                <div className="mt-6 space-y-4">
                  {activeNode.fields.map((field) => (
                    <ConfigField
                      key={field.key}
                      field={field}
                      value={configs[field.key]}
                      onChange={(val) => onChange(field.key, val)}
                    />
                  ))}
                </div>
              ) : (
                <div className="mt-6 rounded-[24px] border border-dashed border-gray-200 bg-gray-50/50 p-6 text-center">
                  <p className="text-sm font-semibold text-gray-500">
                    Milestone này không cần cấu hình thủ công.
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center justify-end gap-3 border-t border-gray-100 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="focus-ring inline-flex h-11 items-center justify-center rounded-full border border-gray-200 bg-white px-6 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition active:scale-95"
              >
                Đóng
              </button>
              <button
                type="button"
                onClick={onClose}
                className="focus-ring eatzy-primary-button h-11 px-6 active:scale-95"
              >
                Xác nhận
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
