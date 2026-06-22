"""Admin report and chart artifact endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from finevent.api.artifacts import (
    artifact_relative_path,
    list_report_artifacts,
    media_type_for_path,
    read_csv_artifact,
    read_jsonl_artifact,
    read_text_artifact,
    resolve_artifact_path,
)

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


@router.get("")
def list_reports(
    kind: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    reports = [artifact.to_dict() for artifact in list_report_artifacts()]
    if kind:
        reports = [artifact for artifact in reports if artifact["kind"] == kind]
    return {
        "items": reports[offset : offset + limit],
        "limit": limit,
        "offset": offset,
        "total": len(reports),
    }


@router.get("/content")
def get_report_content(path: str = Query(...)) -> Any:
    artifact_path = resolve_artifact_path(path)
    if artifact_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}:
        return FileResponse(
            artifact_path,
            media_type=media_type_for_path(artifact_path),
            filename=artifact_path.name,
        )
    return read_text_artifact(path)


@router.get("/table")
def get_report_table(
    path: str = Query(...),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return read_csv_artifact(path, limit=limit, offset=offset)


@router.get("/jsonl")
def get_report_jsonl(
    path: str = Query(...),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return read_jsonl_artifact(path, limit=limit, offset=offset)


@router.get("/charts")
def list_report_charts() -> dict[str, Any]:
    chart_groups = [
        _chart_group(
            "lightweight",
            "Lightweight SVG",
            resolve_artifact_path("reports/evaluation/figures", must_exist=False),
        ),
        _chart_group(
            "dataset",
            "Dataset",
            resolve_artifact_path("reports/evaluation/figures_academic/dataset", must_exist=False),
        ),
        _chart_group(
            "retrieval",
            "Retrieval",
            resolve_artifact_path(
                "reports/evaluation/figures_academic/retrieval",
                must_exist=False,
            ),
        ),
        _chart_group(
            "extraction",
            "Extraction",
            resolve_artifact_path(
                "reports/evaluation/figures_academic/extraction",
                must_exist=False,
            ),
        ),
        _chart_group(
            "verification",
            "Verification",
            resolve_artifact_path(
                "reports/evaluation/figures_academic/verification",
                must_exist=False,
            ),
        ),
    ]
    final_dashboard = resolve_artifact_path(
        "reports/evaluation/figures_academic/final_quality_dashboard.png",
        must_exist=False,
    )
    return {
        "summary_paths": [
            "reports/evaluation/charts_summary.md",
            "reports/evaluation/academic_charts_summary.md",
        ],
        "final_dashboard": (
            artifact_relative_path(final_dashboard) if final_dashboard.exists() else None
        ),
        "groups": chart_groups,
    }


def _chart_group(key: str, title: str, directory: Path) -> dict[str, Any]:
    charts: list[dict[str, Any]] = []
    if directory.exists():
        png_and_svg = sorted(
            path
            for path in directory.glob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".svg"}
        )
        stems = sorted({path.stem for path in png_and_svg})
        for stem in stems:
            png_path = directory / f"{stem}.png"
            svg_path = directory / f"{stem}.svg"
            preferred = png_path if png_path.exists() else svg_path
            charts.append(
                {
                    "key": stem,
                    "title": stem.replace("_", " ").title(),
                    "preferred_path": artifact_relative_path(preferred),
                    "png_path": artifact_relative_path(png_path) if png_path.exists() else None,
                    "svg_path": artifact_relative_path(svg_path) if svg_path.exists() else None,
                    "source_tables": _source_tables_for_group(key),
                }
            )
    return {"key": key, "title": title, "charts": charts}


def _source_tables_for_group(key: str) -> list[str]:
    if key == "retrieval":
        return ["reports/evaluation/retrieval_metrics.csv"]
    if key == "extraction":
        return [
            "reports/evaluation/metrics_by_run.csv",
            "reports/evaluation/per_event_type_metrics.csv",
            "reports/evaluation/errors_by_type.csv",
        ]
    if key == "verification":
        return ["reports/evaluation/hallucination_metrics.csv"]
    if key == "dataset":
        return ["data/labels/events_gold.jsonl"]
    return []
