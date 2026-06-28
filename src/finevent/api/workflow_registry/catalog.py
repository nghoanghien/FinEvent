"""Catalog query and workflow steps assembly services."""

from __future__ import annotations

from typing import Any

from finevent.api.workflow_registry.nodes import WORKFLOW_NODES
from finevent.api.workflow_registry.nodes.m06_extraction import build_steps as build_m06_steps
from finevent.api.workflow_registry.nodes.m08_evaluation import build_steps as build_m08_steps
from finevent.api.workflow_registry.types import BuildContext, WorkflowNodeId, WorkflowStep

WORKFLOW_NODE_BY_ID = {node.id: node for node in WORKFLOW_NODES}

EDGE_LABELS = {
    "m00_runtime->m01_ingestion": "Db Connection",
    "m01_ingestion->m02_labeling": "Clean Articles",
    "m01_ingestion->m03_rag": "Clean Articles",
    "m02_labeling->m03_rag": "Gold Labels",
    "m02_labeling->m04_retrieval": "Gold Labels",
    "m03_rag->m04_retrieval": "RAG Index + Chunk Patterns",
    "m04_retrieval->m06_extraction": "Retrieved Contexts",
    "m06_extraction->m07_verification": "Student Predictions",
    "m04_retrieval->m08_evaluation": "Retrieval Metrics",
    "m07_verification->m08_evaluation": "Verified Events",
}


def workflow_catalog() -> list[dict[str, Any]]:
    return [node.to_catalog_item() for node in WORKFLOW_NODES]


def build_workflow_steps(
    workflow_name: str,
    config: dict[str, Any],
    *,
    run_id: str | None = None,
) -> list[WorkflowStep]:
    if workflow_name == "milestone_graph":
        selected_node_ids = _selected_node_ids(config)
        _validate_selected_nodes(selected_node_ids)
        return _build_selected_node_steps(config, selected_node_ids, run_id=run_id)

    if workflow_name == "evaluation":
        return build_m08_steps(
            BuildContext(config=config, selected_node_ids=("m08_evaluation",))
        )
    if workflow_name == "student_batch_extraction":
        return build_m06_steps(
            BuildContext(config=config, selected_node_ids=("m06_extraction",), run_id=run_id)
        )
    if workflow_name == "student_batch_with_evaluation":
        context = BuildContext(
            config=config,
            selected_node_ids=("m06_extraction", "m07_verification", "m08_evaluation"),
            run_id=run_id,
        )
        return build_m06_steps(context) + build_m08_steps(context)

    raise ValueError(
        "Unknown workflow_name. Allowed values: milestone_graph, evaluation, "
        "student_batch_extraction, student_batch_with_evaluation."
    )


def _build_selected_node_steps(
    config: dict[str, Any],
    selected_node_ids: tuple[WorkflowNodeId, ...],
    *,
    run_id: str | None,
) -> list[WorkflowStep]:
    context = BuildContext(config=config, selected_node_ids=selected_node_ids, run_id=run_id)
    steps: list[WorkflowStep] = []
    for node_id in selected_node_ids:
        node_context = BuildContext(
            config=_node_config(config, node_id),
            selected_node_ids=selected_node_ids,
            run_id=run_id,
            python=context.python,
        )
        steps.extend(WORKFLOW_NODE_BY_ID[node_id].build_steps(node_context))
    if not steps:
        raise ValueError("Select at least one runnable milestone node.")
    return steps


def _node_config(config: dict[str, Any], node_id: WorkflowNodeId) -> dict[str, Any]:
    node_configs = config.get("node_configs")
    if not isinstance(node_configs, dict):
        return config
    raw_node_config = node_configs.get(node_id)
    if not isinstance(raw_node_config, dict):
        return config
    return {**config, **raw_node_config}


def _selected_node_ids(config: dict[str, Any]) -> tuple[WorkflowNodeId, ...]:
    raw_nodes = config.get("selected_nodes")
    if not isinstance(raw_nodes, list):
        raise ValueError("milestone_graph requires config.selected_nodes.")
    selected = [str(node_id) for node_id in raw_nodes]
    return tuple(node.id for node in WORKFLOW_NODES if node.id in selected)


def _validate_selected_nodes(selected_node_ids: tuple[WorkflowNodeId, ...]) -> None:
    if not selected_node_ids:
        raise ValueError("Select at least one milestone node.")
    selected = set(selected_node_ids)
    unknown = selected - set(WORKFLOW_NODE_BY_ID)
    if unknown:
        raise ValueError(f"Unknown workflow node(s): {', '.join(sorted(unknown))}.")
    for node_id in selected_node_ids:
        missing = [dep for dep in WORKFLOW_NODE_BY_ID[node_id].depends_on if dep not in selected]
        if missing:
            missing_text = ", ".join(WORKFLOW_NODE_BY_ID[dep].milestone for dep in missing)
            node = WORKFLOW_NODE_BY_ID[node_id]
            raise ValueError(f"{node.milestone} requires prerequisite node(s): {missing_text}.")
