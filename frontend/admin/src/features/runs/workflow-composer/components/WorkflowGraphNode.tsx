"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { HelpCircle, Settings, Lock, CheckCircle2, Plus, X } from "lucide-react";
import type { WorkflowNodeDefinition, WorkflowNodeStatus } from "../types";

type WorkflowGraphNodeProps = {
  node: WorkflowNodeDefinition;
  status: WorkflowNodeStatus;
  isActive: boolean;
  onToggle: () => void;
  onEditClick: () => void;
  dependsOnMilestones: string[];
};

const accentClasses = {
  sky: "bg-sky-50 text-sky-700 border-sky-100/50",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-100/50",
  amber: "bg-amber-50 text-amber-700 border-amber-100/50",
};

export function WorkflowGraphNode({
  node,
  status,
  isActive,
  onToggle,
  onEditClick,
  dependsOnMilestones,
}: WorkflowGraphNodeProps) {
  const isSelected = status === "selected";
  const isBlocked = status === "blocked";
  const Icon = node.icon;

  const [isTooltipVisible, setIsTooltipVisible] = useState(false);
  const [tooltipCoords, setTooltipCoords] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  const handleMouseEnter = () => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setTooltipCoords({
        top: rect.top + window.scrollY,
        left: rect.left + rect.width / 2 + window.scrollX,
      });
      setIsTooltipVisible(true);
    }
  };

  const handleMouseLeave = () => {
    setIsTooltipVisible(false);
  };

  // Recalculate position on scroll (including internal container scroll) or resize
  useEffect(() => {
    if (!isTooltipVisible) return;

    const updatePosition = () => {
      if (buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        setTooltipCoords({
          top: rect.top + window.scrollY,
          left: rect.left + rect.width / 2 + window.scrollX,
        });
      }
    };

    window.addEventListener("scroll", updatePosition, { capture: true, passive: true });
    window.addEventListener("resize", updatePosition, { passive: true });

    return () => {
      window.removeEventListener("scroll", updatePosition, { capture: true });
      window.removeEventListener("resize", updatePosition);
    };
  }, [isTooltipVisible]);

  return (
    <div
      id={`node-${node.id}`}
      className={[
        "relative flex flex-col justify-between rounded-[40px] border bg-white p-5 text-left transition-all duration-300 min-h-[140px]",
        isSelected
          ? "border-primary/50 bg-white shadow-xl shadow-primary/5 ring-1 ring-primary/20 scale-[1.01]"
          : "border-gray-100 bg-white shadow-md hover:-translate-y-0.5 hover:shadow-finevent-hover",
        isBlocked ? "cursor-not-allowed bg-gray-50/50 opacity-40 hover:-translate-y-0 hover:shadow-none shadow-none" : "",
        isActive && isSelected ? "ring-2 ring-primary ring-offset-2" : "",
      ].join(" ")}
    >
      {/* Centered top border milestone badge */}
      <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border border-lime-100 bg-lime-50 px-3.5 py-0.5 text-[10px] font-black uppercase text-primary shadow-sm">
        {node.milestone}
      </span>

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mt-1">
        <div
          className={[
            "flex h-11 w-11 items-center justify-center rounded-2xl border",
            accentClasses[node.accent] || accentClasses.sky,
          ].join(" ")}
        >
          <Icon className="h-5 w-5" />
        </div>

        {/* Action button grouping */}
        <div className="flex items-center gap-2">
          {/* Tooltip Description */}
          <div>
            <button
              ref={buttonRef}
              type="button"
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
              className="flex h-7 w-7 items-center justify-center rounded-full border border-gray-100 bg-gray-50/50 text-gray-400 hover:text-gray-600 transition"
            >
              <HelpCircle className="h-4 w-4" />
            </button>
            {mounted && createPortal(
              <AnimatePresence>
                {isTooltipVisible && (
                  <div
                    style={{
                      position: "absolute",
                      top: `${tooltipCoords.top}px`,
                      left: `${tooltipCoords.left}px`,
                      transform: "translate(-50%, -100%)",
                      pointerEvents: "none",
                      zIndex: 99999,
                    }}
                  >
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: 6 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: 6 }}
                      transition={{ duration: 0.15, ease: "easeOut" }}
                      className="w-64 rounded-2xl bg-ink-900/95 p-3 text-xs leading-relaxed text-white shadow-2xl border border-white/10 backdrop-blur-md"
                    >
                      {node.description}
                      <div className="absolute top-full left-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1 bg-[#111827] rotate-45 border-r border-b border-white/10" />
                    </motion.div>
                  </div>
                )}
              </AnimatePresence>,
              document.body
            )}
          </div>

          {/* Settings config button */}
          {isSelected ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onEditClick();
              }}
              title="Cấu hình node"
              className="focus-ring flex h-7 w-7 items-center justify-center rounded-full border border-lime-200 bg-lime-50 text-lime-700 hover:bg-primary hover:text-white transition shadow-sm active:scale-90"
            >
              <Settings className="h-3.5 w-3.5" />
            </button>
          ) : null}
        </div>
      </div>

      {/* Title / Info */}
      <div className="mt-4 flex-1">
        <h4 className="font-anton text-lg font-black uppercase text-gray-900 tracking-wide">
          {node.shortTitle}
        </h4>
      </div>

      {/* Footer controls */}
      <div className="mt-5 flex items-center justify-between gap-3">
        <span className="text-[10px] font-black uppercase text-gray-400">
          {dependsOnMilestones.length === 0 ? "Root" : `Sau ${dependsOnMilestones.join(", ")}`}
        </span>

        <button
          type="button"
          disabled={isBlocked}
          onClick={onToggle}
          className={[
            "inline-flex h-9 items-center gap-1.5 rounded-full px-3.5 text-xs font-black uppercase transition duration-200 active:scale-95",
            isSelected
              ? "bg-rose-50 text-rose-700 hover:bg-rose-100"
              : isBlocked
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-gray-900 text-white hover:bg-ink-700",
          ].join(" ")}
        >
          {isSelected ? (
            <>
              <X className="h-3.5 w-3.5" />
              Tắt
            </>
          ) : isBlocked ? (
            <>
              <Lock className="h-3 w-3" />
              Khóa
            </>
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" />
              Bật
            </>
          )}
        </button>
      </div>

      {/* Selected Indicator */}
      {isSelected ? (
        <div className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white shadow-md border border-white animate-[fadeInUp_0.2s_ease-out]">
          <CheckCircle2 className="h-3 w-3 stroke-[3px]" />
        </div>
      ) : null}
    </div>
  );
}
