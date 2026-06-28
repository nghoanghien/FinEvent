"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Handle, Position } from "@xyflow/react";
import { HelpCircle, Settings, Lock, Plus, X, Check } from "lucide-react";
import { isNodeConfigurable, type WorkflowNodeDefinition, type WorkflowNodeStatus } from "../types";

type WorkflowNodeData = {
  node: WorkflowNodeDefinition;
  status: WorkflowNodeStatus;
  isActive: boolean;
  onToggle: () => void;
  onEditClick: () => void;
  dependsOnMilestones: string[];
};

const getWatermarkStyles = (status: WorkflowNodeStatus) => {
  if (status === "selected") {
    return {
      className: "text-lime-600",
      style: { opacity: 0.15 },
    };
  }
  if (status === "blocked") {
    return {
      className: "text-slate-500",
      style: { opacity: 0.04 },
    };
  }
  return {
    className: "text-slate-600",
    style: { opacity: 0.08 },
  };
};

export function WorkflowNode({ data }: { data: WorkflowNodeData }) {
  const { node, status, isActive, onToggle, onEditClick, dependsOnMilestones } = data;
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

  const handleCardClick = () => {
    if (isBlocked) return;
    onToggle();
  };

  return (
    <div
      onClick={handleCardClick}
      style={{ cursor: isBlocked ? "not-allowed" : "pointer" }}
      className={[
        "relative flex flex-col justify-between rounded-[28px] border-4 p-4 text-left transition-all duration-300 w-[190px] min-h-[120px] select-none group",
        isSelected
          ? "border-lime-200 bg-lime-50/90 shadow-md ring-1 ring-lime-500/10"
          : isBlocked
            ? "border-gray-200/70 bg-gray-50 shadow-sm"
            : "border-gray-200/80 bg-white shadow-md hover:border-gray-300 hover:bg-gray-50/50 hover:shadow-lg",
        isActive && isSelected ? "ring-2 ring-primary ring-offset-2" : "",
      ].join(" ")}
    >
      {/* Handles for flow connections */}
      {node.id !== "m00_runtime" && (
        <Handle
          type="target"
          position={Position.Left}
          className={[
            "!w-2.5 !h-2.5 !border-2 !transition-colors !left-[-6px] !top-1/2 !-translate-y-1/2",
            isSelected
              ? "!bg-primary !border-primary"
              : "!bg-white !border-slate-300 hover:!bg-slate-400 hover:!border-slate-400",
          ].join(" ")}
        />
      )}

      {node.id !== "m08_evaluation" && (
        <Handle
          type="source"
          position={Position.Right}
          className={[
            "!w-2.5 !h-2.5 !border-2 !transition-colors !right-[-6px] !top-1/2 !-translate-y-1/2",
            isSelected
              ? "!bg-primary !border-primary"
              : "!bg-white !border-slate-300 hover:!bg-slate-400 hover:!border-slate-400",
          ].join(" ")}
        />
      )}

      {/* Centered top border milestone badge */}
      <span className={[
        "absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full border px-3.5 py-1 text-[11px] font-black uppercase shadow-sm z-10 whitespace-nowrap transition-colors duration-300",
        isSelected
          ? "border-lime-100 bg-lime-50 text-primary"
          : isBlocked
            ? "border-gray-200 bg-gray-100 text-gray-400"
            : "border-lime-100 bg-lime-50 text-primary",
      ].join(" ")}>
        {node.milestone}
      </span>

      {/* Background Watermark Icon */}
      {(() => {
        const styles = getWatermarkStyles(status);
        return (
          <Icon
            className={[
              "absolute right-2 top-1/2 -translate-y-1/2 w-20 h-20 pointer-events-none transition-all duration-300 z-0",
              styles.className,
            ].join(" ")}
            style={styles.style}
            strokeWidth={3.0}
          />
        );
      })()}

      {/* Content wrapper */}
      <div className="flex flex-col justify-between flex-1 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 mt-1 min-h-[24px]">
          {/* Title */}
          <div className={["min-w-0 flex-1", isBlocked ? "opacity-40" : ""].join(" ")}>
            <h4
              className="font-anton text-lg font-black uppercase text-gray-700 tracking-wide leading-none select-none"
              style={{ WebkitTextStroke: "0.35px currentColor" }}
            >
              {node.shortTitle}
            </h4>
          </div>

          {/* Action button grouping */}
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Tooltip Description */}
            <div>
              <button
                ref={buttonRef}
                type="button"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                onClick={(e) => e.stopPropagation()}
                className="flex h-6 w-6 items-center justify-center rounded-full border border-gray-200 bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-800 hover:border-gray-300 transition shadow-sm active:scale-90 nodrag !cursor-pointer"
              >
                <HelpCircle className="h-3.5 w-3.5 stroke-[3px]" />
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
                        className="w-60 rounded-2xl bg-slate-900/95 p-3 text-[11px] leading-relaxed text-white shadow-2xl border border-white/10 backdrop-blur-md"
                      >
                        {node.description}
                        <div className="absolute top-full left-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1 bg-slate-900 rotate-45 border-r border-b border-white/10" />
                      </motion.div>
                    </div>
                  )}
                </AnimatePresence>,
                document.body
              )}
            </div>

            {/* Settings config button */}
            {isSelected && isNodeConfigurable(node) ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEditClick();
                }}
                title="Cấu hình node"
                className="focus-ring flex h-6 w-6 items-center justify-center rounded-full border border-lime-300 bg-lime-100 text-lime-800 hover:bg-primary hover:text-white transition shadow-sm active:scale-90 nodrag"
              >
                <Settings className="h-3.5 w-3.5 stroke-[3px]" />
              </button>
            ) : null}
          </div>
        </div>

        {/* Footer controls (FinEvent checkmark toggle styling) */}
        <div className="mt-3.5 flex items-center justify-between gap-2">
          <span className={[
            "text-[9px] font-black uppercase truncate max-w-[120px]",
            isBlocked ? "text-gray-400 opacity-40" : "text-gray-400"
          ].join(" ")}>
            {dependsOnMilestones.length === 0 ? "Root" : `Sau ${dependsOnMilestones.join(", ")}`}
          </span>

          <div className="flex items-center">
            {isSelected ? (
              <div className="w-6 h-6 rounded-full bg-lime-500 text-white flex items-center justify-center transition-all duration-300 shadow-sm">
                <Check className="w-3.5 h-3.5 stroke-[4px]" />
              </div>
            ) : isBlocked ? (
              <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center transition-all duration-300">
                <Lock className="w-3 h-3" />
              </div>
            ) : (
              <div className="w-6 h-6 rounded-full bg-gray-100 text-transparent flex items-center justify-center transition-all duration-300 border border-gray-200/60 group-hover:bg-gray-200/60 group-hover:border-gray-300">
                <Check className="w-3.5 h-3.5 stroke-[4px] opacity-0 group-hover:opacity-40 group-hover:text-gray-500 transition-opacity" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
