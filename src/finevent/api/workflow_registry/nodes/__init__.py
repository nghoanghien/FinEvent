"""Nodes registration package."""

from __future__ import annotations

from finevent.api.workflow_registry.nodes.m00_runtime import node_spec as m00_runtime_spec
from finevent.api.workflow_registry.nodes.m01_ingestion import node_spec as m01_ingestion_spec
from finevent.api.workflow_registry.nodes.m02_labeling import node_spec as m02_labeling_spec
from finevent.api.workflow_registry.nodes.m03_rag import node_spec as m03_rag_spec
from finevent.api.workflow_registry.nodes.m04_retrieval import node_spec as m04_retrieval_spec
from finevent.api.workflow_registry.nodes.m06_extraction import node_spec as m06_extraction_spec
from finevent.api.workflow_registry.nodes.m07_verification import node_spec as m07_verification_spec
from finevent.api.workflow_registry.nodes.m08_evaluation import node_spec as m08_evaluation_spec

WORKFLOW_NODES = (
    m00_runtime_spec,
    m01_ingestion_spec,
    m02_labeling_spec,
    m03_rag_spec,
    m04_retrieval_spec,
    m06_extraction_spec,
    m07_verification_spec,
    m08_evaluation_spec,
)
