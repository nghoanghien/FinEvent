from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finevent.api.job_runner import build_workflow_steps  # noqa: E402
from finevent.api.main import app  # noqa: E402
from finevent.api.workflow_registry.catalog import workflow_catalog  # noqa: E402


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
    catalog = client.get("/admin/workflows/catalog", headers=_admin_headers())
    invalid = client.post(
        "/admin/runs",
        json={"workflow_name": "unknown_workflow", "config": {}},
        headers=_admin_headers(),
    )

    assert runs.status_code == 200
    assert runs.json()["total"] == 0
    assert catalog.status_code == 200
    assert any(item["id"] == "m08_evaluation" for item in catalog.json()["items"])
    assert invalid.status_code == 422
    assert invalid.json()["error_code"] == "UNKNOWN_WORKFLOW"


def test_workflow_step_filters_articles_by_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_path = tmp_path / "data" / "processed" / "articles_clean.jsonl"
    articles_path.parent.mkdir(parents=True)
    articles_path.write_text(
        "\n".join(
            [
                json.dumps({"article_id": "a1", "source": "cafef"}, ensure_ascii=False),
                json.dumps({"article_id": "a2", "source": "vietstock"}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FINEVENT_WORKSPACE_ROOT", str(tmp_path))

    steps = build_workflow_steps(
        "student_batch_extraction",
        {
            "articles_path": "data/processed/articles_clean.jsonl",
            "sources": ["cafef"],
        },
        run_id="admin_run_test",
    )

    filtered_path = tmp_path / steps[0].command[steps[0].command.index("--articles-path") + 1]
    rows = [json.loads(line) for line in filtered_path.read_text(encoding="utf-8").splitlines()]
    assert filtered_path == (
        tmp_path / "runs" / "admin" / "admin_run_test" / "inputs" / "articles_filtered.jsonl"
    )
    assert rows == [{"article_id": "a1", "source": "cafef"}]


def test_m01_catalog_exposes_sources_reset_and_html_targets() -> None:
    catalog = workflow_catalog()
    m01 = next(item for item in catalog if item["id"] == "m01_ingestion")
    fields = {field["key"]: field for field in m01["fields"]}

    assert m01["default_config"]["sources"] == [
        "cafef",
        "vietstock",
        "tinnhanhchungkhoan",
        "nhadautu",
    ]
    assert m01["default_config"]["discover_download"] is True
    assert m01["default_config"]["reset_html_snapshots"] is False
    assert fields["sources"]["type"] == "multi-select"
    assert fields["reset_html_snapshots"]["type"] == "checkbox"
    assert fields["articles_path"]["configurable"] is False
    assert fields["input_html_dir"]["configurable"] is False
    assert fields["html_manifest_path"]["configurable"] is False
    assert fields["min_text_chars"]["label"] == "Số ký tự text tối thiểu"
    assert "số ký tự sau khi normalize text" in fields["min_text_chars"]["description"]


def test_m01_build_command_passes_sources_reset_and_manifest() -> None:
    steps = build_workflow_steps(
        "milestone_graph",
        {
            "selected_nodes": ["m00_runtime", "m01_ingestion"],
            "sources": ["nhadautu"],
            "node_configs": {
                "m01_ingestion": {
                    "discover_download": True,
                    "sources": ["cafef", "vietstock"],
                    "reset_html_snapshots": True,
                    "max_articles": 7,
                    "max_discovered_urls": 11,
                    "html_manifest_path": "data/raw/html_manifest.jsonl",
                }
            },
        },
        run_id="admin_run_test",
    )
    m01_step = next(step for step in steps if step.step_id == "m01_data_ingestion")
    command = m01_step.command

    assert "--html-manifest-path" in command
    assert "--reset-html-snapshots" in command
    assert "--discover" in command
    assert command[command.index("--max-download-articles") + 1] == "7"
    assert command[command.index("--max-discovered-urls") + 1] == "11"
    assert _flag_values(command, "--source") == ["cafef", "vietstock"]
    assert "nhadautu" not in _flag_values(command, "--source")


def test_m01_build_command_rejects_discover_without_sources() -> None:
    with pytest.raises(ValueError, match="at least one source"):
        build_workflow_steps(
            "milestone_graph",
            {
                "selected_nodes": ["m00_runtime", "m01_ingestion"],
                "node_configs": {
                    "m01_ingestion": {
                        "discover_download": True,
                        "sources": [],
                    }
                },
            },
            run_id="admin_run_test",
        )


def test_m02_catalog_defaults_to_strict_validation_and_explains_limits() -> None:
    catalog = workflow_catalog()
    m02 = next(item for item in catalog if item["id"] == "m02_labeling")
    fields = {field["key"]: field for field in m02["fields"]}

    assert m02["default_config"]["strict_validation"] is True
    assert fields["max_articles"]["label"] == "Số bài teacher xử lý tối đa"
    assert "retry không tính vào giới hạn" in fields["max_articles"]["description"]

    steps = build_workflow_steps(
        "milestone_graph",
        {"selected_nodes": ["m00_runtime", "m01_ingestion", "m02_labeling"]},
        run_id="admin_run_test",
    )
    validate_step = next(step for step in steps if step.step_id == "m02_validate_labels")
    assert "--strict-validation" in validate_step.command


def test_m04_catalog_and_command_default_to_student_listwise_rerank() -> None:
    catalog = workflow_catalog()
    m04 = next(item for item in catalog if item["id"] == "m04_retrieval")
    fields = {field["key"]: field for field in m04["fields"]}

    assert m04["default_config"]["llm_rerank_mode"] == "student_env"
    assert m04["default_config"]["llm_rerank_top_n"] == 15
    assert fields["llm_rerank_mode"]["type"] == "select"
    assert fields["llm_rerank_top_n"]["type"] == "number"
    assert "student model" in fields["llm_rerank_mode"]["description"]

    steps = build_workflow_steps(
        "milestone_graph",
        {
            "selected_nodes": [
                "m00_runtime",
                "m01_ingestion",
                "m02_labeling",
                "m03_rag",
                "m04_retrieval",
            ]
        },
        run_id="admin_run_test",
    )
    m04_step = next(step for step in steps if step.step_id == "m04_online_retrieval")
    command = m04_step.command

    assert command[command.index("--llm-rerank-mode") + 1] == "student_env"
    assert command[command.index("--llm-rerank-top-n") + 1] == "15"
    assert "--llm-rerank-max-query-article-chars" in command
    assert "--llm-rerank-max-candidate-chars" in command


def test_milestone_graph_rejects_missing_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fixture_workspace(tmp_path)
    monkeypatch.setenv("FINEVENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FINEVENT_ADMIN_API_KEY", "test-admin-key")
    monkeypatch.delenv("FINEVENT_ADMIN_AUTH_DISABLED", raising=False)
    client = TestClient(app)

    response = client.post(
        "/admin/runs",
        json={
            "workflow_name": "milestone_graph",
            "config": {"selected_nodes": ["m08_evaluation"]},
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_WORKFLOW_CONFIG"
    assert "requires prerequisite" in response.json()["message"]


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


def _flag_values(command: list[str], flag: str) -> list[str]:
    return [command[index + 1] for index, item in enumerate(command[:-1]) if item == flag]


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
