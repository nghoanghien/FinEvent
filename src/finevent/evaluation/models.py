"""Data models for end-to-end evaluation and ablation artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class GoldRecord:
    article_id: str
    label: JsonDict
    source_record: JsonDict = field(default_factory=dict)

    @property
    def events(self) -> list[JsonDict]:
        events = self.label.get("events")
        if not isinstance(events, list):
            return []
        return [event for event in events if isinstance(event, dict)]

    @property
    def document_label(self) -> str:
        return str(self.label.get("document_label") or "NO_EVENT")

    def to_dict(self) -> JsonDict:
        return {
            "article_id": self.article_id,
            "label": self.label,
            "source_record": self.source_record,
        }


@dataclass(frozen=True)
class PredictionRecord:
    article_id: str
    config_name: str
    prediction: JsonDict
    run_id: str = ""
    source_path: str = ""
    validation_issues: list[JsonDict] = field(default_factory=list)
    verification_report: JsonDict = field(default_factory=dict)
    hallucination_metrics: JsonDict = field(default_factory=dict)
    raw_record: JsonDict = field(default_factory=dict)
    json_valid: bool = True

    @property
    def events(self) -> list[JsonDict]:
        events = self.prediction.get("events")
        if not isinstance(events, list):
            return []
        return [event for event in events if isinstance(event, dict)]

    @property
    def document_label(self) -> str:
        return str(self.prediction.get("document_label") or "NO_EVENT")

    @property
    def schema_valid(self) -> bool:
        for issue in self.validation_issues:
            if isinstance(issue, dict) and issue.get("severity") == "error":
                return False
        return bool(self.json_valid)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class EventMatch:
    gold_index: int
    pred_index: int
    gold_event: JsonDict
    pred_event: JsonDict
    score: float
    score_breakdown: JsonDict

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationRunResult:
    config_name: str
    article_count: int
    gold_event_count: int
    predicted_event_count: int
    matched_event_count: int
    metrics: JsonDict
    per_event_type_rows: list[JsonDict]
    error_rows: list[JsonDict]
    hallucination_row: JsonDict
    detailed_rows: list[JsonDict]

    def metrics_row(self) -> JsonDict:
        return {
            "config_name": self.config_name,
            "article_count": self.article_count,
            "gold_event_count": self.gold_event_count,
            "predicted_event_count": self.predicted_event_count,
            "matched_event_count": self.matched_event_count,
            **self.metrics,
        }
