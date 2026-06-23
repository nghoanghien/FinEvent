from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finevent.api.main import app  # noqa: E402


def test_admin_report_and_output_endpoints_use_safe_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fixture_workspace(tmp_path)
    monkeypatch.setenv("FINEVENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FINEVENT_ADMIN_API_KEY", "test-admin-key")
    monkeypatch.delenv("FINEVENT_ADMIN_AUTH_DISABLED", raising=False)
    headers = _admin_headers()
    client = TestClient(app)

    public_health = client.get("/health")
    unauthenticated = client.get("/admin/reports")
    health = client.get("/admin/health", headers=headers)
    reports = client.get("/admin/reports", headers=headers)
    markdown = client.get(
        "/admin/reports/content",
        params={"path": "reports/evaluation/eval_summary.md"},
        headers=headers,
    )
    table = client.get(
        "/admin/reports/table",
        params={"path": "reports/evaluation/metrics_by_run.csv"},
        headers=headers,
    )
    jsonl = client.get(
        "/admin/reports/jsonl",
        params={"path": "reports/evaluation/error_examples.jsonl"},
        headers=headers,
    )
    charts = client.get("/admin/reports/charts", headers=headers)
    outputs = client.get(
        "/admin/outputs",
        params={"source": "filesystem"},
        headers=headers,
    )
    output_detail = client.get("/admin/outputs/run_001", headers=headers)
    output_by_article = client.get(
        "/admin/outputs/by-article/article_001",
        headers=headers,
    )
    traversal = client.get(
        "/admin/reports/content",
        params={"path": "reports/../.env"},
        headers=headers,
    )

    assert public_health.status_code == 200
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error_code"] == "ADMIN_AUTH_REQUIRED"
    assert health.status_code == 200
    assert health.json()["api"] == "ok"
    assert reports.status_code == 200
    assert any(
        item["path"] == "reports/evaluation/metrics_by_run.csv"
        for item in reports.json()["items"]
    )
    assert markdown.status_code == 200
    assert "Evaluation Summary" in markdown.json()["content"]
    assert table.status_code == 200
    assert table.json()["columns"] == ["config_name", "event_detection_f1"]
    assert table.json()["rows"][0]["config_name"] == "workflow"
    assert jsonl.status_code == 200
    assert jsonl.json()["rows"][0]["error_code"] == "E_MISSED_EVENT"
    assert charts.status_code == 200
    assert charts.json()["final_dashboard"] == (
        "reports/evaluation/figures_academic/final_quality_dashboard.png"
    )
    assert outputs.status_code == 200
    assert outputs.json()["items"][0]["run_id"] == "run_001"
    assert output_detail.status_code == 200
    assert output_detail.json()["output"]["article_id"] == "article_001"
    assert output_by_article.status_code == 200
    assert output_by_article.json()["output"]["article_id"] == "article_001"
    assert traversal.status_code == 403
    assert traversal.json()["error_code"] == "ARTIFACT_ROOT_NOT_ALLOWED"


def test_admin_runs_list_and_unknown_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fixture_workspace(tmp_path)
    monkeypatch.setenv("FINEVENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FINEVENT_ADMIN_API_KEY", "test-admin-key")
    monkeypatch.delenv("FINEVENT_ADMIN_AUTH_DISABLED", raising=False)
    client = TestClient(app)

    runs = client.get("/admin/runs", headers=_admin_headers())
    invalid = client.post(
        "/admin/runs",
        json={"workflow_name": "unknown_workflow", "config": {}},
        headers=_admin_headers(),
    )

    assert runs.status_code == 200
    assert runs.json()["total"] == 0
    assert invalid.status_code == 422
    assert invalid.json()["error_code"] == "UNKNOWN_WORKFLOW"


def test_admin_run_queue_limit_and_startup_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fixture_workspace(tmp_path)
    stale_run_dir = tmp_path / "runs" / "admin" / "admin_run_stale"
    stale_run_dir.mkdir(parents=True)
    (stale_run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": "admin_run_stale",
                "workflow_name": "evaluation",
                "status": "running",
                "config": {},
                "steps": [
                    {
                        "step_id": "m08_evaluation",
                        "status": "running",
                        "started_at": "2026-06-23T00:00:00+00:00",
                    }
                ],
                "created_at": "2026-06-23T00:00:00+00:00",
                "started_at": "2026-06-23T00:00:00+00:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FINEVENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FINEVENT_ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("FINEVENT_MAX_QUEUE_SIZE", "0")
    monkeypatch.delenv("FINEVENT_ADMIN_AUTH_DISABLED", raising=False)

    with TestClient(app) as client:
        reconciled = client.get("/admin/runs/admin_run_stale", headers=_admin_headers())
        queued = client.post(
            "/admin/runs",
            json={"workflow_name": "evaluation", "config": {}},
            headers=_admin_headers(),
        )

    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "interrupted"
    assert reconciled.json()["steps"][0]["status"] == "interrupted"
    assert queued.status_code == 429
    assert queued.json()["error_code"] == "RUN_QUEUE_FULL"


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-API-Key": "test-admin-key"}


def _write_fixture_workspace(root: Path) -> None:
    evaluation_dir = root / "reports" / "evaluation"
    figures_dir = evaluation_dir / "figures_academic"
    extraction_run_dir = root / "runs" / "extraction" / "run_001"
    evaluation_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    extraction_run_dir.mkdir(parents=True)
    (root / ".env").write_text("SECRET=hidden\n", encoding="utf-8")
    (evaluation_dir / "eval_summary.md").write_text("# Evaluation Summary\n", encoding="utf-8")
    (evaluation_dir / "metrics_by_run.csv").write_text(
        "config_name,event_detection_f1\nworkflow,0.8\n",
        encoding="utf-8",
    )
    (evaluation_dir / "error_examples.jsonl").write_text(
        json.dumps({"error_code": "E_MISSED_EVENT"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (evaluation_dir / "charts_summary.md").write_text("# Charts\n", encoding="utf-8")
    (evaluation_dir / "academic_charts_summary.md").write_text(
        "# Academic Charts\n",
        encoding="utf-8",
    )
    (figures_dir / "final_quality_dashboard.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (extraction_run_dir / "result.json").write_text(
        json.dumps(
            {
                "article_id": "article_001",
                "document_label": "HAS_EVENT",
                "events": [{"event_id": "event_001"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
