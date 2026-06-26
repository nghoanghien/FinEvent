"""Core workflow registry types."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

WorkflowNodeId = str
StepBuilder = Callable[["BuildContext"], list["WorkflowStep"]]


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    milestone: str
    name: str
    command: list[str]
    expected_artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuildContext:
    config: dict[str, Any]
    selected_node_ids: tuple[WorkflowNodeId, ...]
    run_id: str | None = None
    python: str = field(default_factory=lambda: sys.executable)

    def selected(self, node_id: WorkflowNodeId) -> bool:
        return node_id in self.selected_node_ids


@dataclass(frozen=True)
class WorkflowFieldSpec:
    key: str
    label: str
    type: str  # "text" | "number" | "select" | "checkbox" | "multi-select"
    description: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[dict[str, str]] | None = None
    configurable: bool = True


@dataclass(frozen=True)
class WorkflowNodeSpec:
    id: WorkflowNodeId
    milestone: str
    title: str
    description: str
    depends_on: tuple[WorkflowNodeId, ...]
    default_config: dict[str, Any]
    expected_artifacts: tuple[str, ...]
    build_steps: StepBuilder
    fields: tuple[WorkflowFieldSpec, ...] = ()

    def to_catalog_item(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "milestone": self.milestone,
            "title": self.title,
            "description": self.description,
            "depends_on": list(self.depends_on),
            "default_config": self.default_config,
            "expected_artifacts": list(self.expected_artifacts),
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "description": f.description,
                    "min": f.min,
                    "max": f.max,
                    "step": f.step,
                    "options": f.options,
                    "configurable": f.configurable,
                }
                for f in self.fields
            ],
        }
