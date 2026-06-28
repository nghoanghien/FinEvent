"""Data models for online extraction workflow artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class ExtractionRunConfig:
    retrieval_config: str = "metadata_aware_hybrid"
    max_contexts: int = 5
    student_model: str = "deterministic_student_v1"
    prompt_version: str = "m06_extraction_v1"
    use_retrieval: bool = True
    allow_zero_context: bool = True
    enable_verification: bool = True
    evidence_match_threshold: float = 0.82
    argument_match_threshold: float = 0.78
    drop_unsupported_events: bool = True
    null_unsupported_arguments: bool = True
    verification_version: str = "m07_verification_v1"
    run_label: str = "m06_online_extraction"
    max_article_chars: int = 0
    max_context_chars: int = 0
    max_pattern_output_chars: int = 0
    max_prompt_chars: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict | None) -> ExtractionRunConfig:
        if not data:
            return cls()
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class NodeTrace:
    node: str
    status: str
    latency_ms: float
    input_summary: JsonDict = field(default_factory=dict)
    output_summary: JsonDict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class ExtractionWorkflowState:
    run_id: str
    config: ExtractionRunConfig
    input_payload: JsonDict
    article: JsonDict | None = None
    retrieval_run_id: str | None = None
    query_plan: list[JsonDict] = field(default_factory=list)
    retrieved_contexts: list[JsonDict] = field(default_factory=list)
    selected_patterns: list[JsonDict] = field(default_factory=list)
    extraction_prompt: str = ""
    raw_model_output: str | JsonDict | None = None
    draft_output: JsonDict | None = None
    final_output: JsonDict | None = None
    verification_report: JsonDict | None = None
    hallucination_metrics: JsonDict = field(default_factory=dict)
    validation_issues: list[JsonDict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    traces: list[NodeTrace] = field(default_factory=list)
    run_dir: str | None = None

    def to_dict(self) -> JsonDict:
        return {
            "run_id": self.run_id,
            "config": self.config.to_dict(),
            "input_payload": self.input_payload,
            "article": self.article,
            "retrieval_run_id": self.retrieval_run_id,
            "query_plan": self.query_plan,
            "retrieved_contexts": self.retrieved_contexts,
            "selected_patterns": self.selected_patterns,
            "extraction_prompt": self.extraction_prompt,
            "raw_model_output": self.raw_model_output,
            "draft_output": self.draft_output,
            "final_output": self.final_output,
            "verification_report": self.verification_report,
            "hallucination_metrics": self.hallucination_metrics,
            "validation_issues": self.validation_issues,
            "warnings": self.warnings,
            "errors": self.errors,
            "traces": [trace.to_dict() for trace in self.traces],
            "run_dir": self.run_dir,
        }


@dataclass(frozen=True)
class ValidationRepairResult:
    output: JsonDict
    issues: list[JsonDict]
    repaired: bool
    parse_error: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)
