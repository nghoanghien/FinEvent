"""Machine-readable event taxonomy loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from finevent.paths import resolve_project_path
from finevent.types import JsonDict, PathLike

DEFAULT_TAXONOMY_PATH = "data/schema/event_taxonomy_v1.json"


@dataclass(frozen=True)
class EventTaxonomy:
    schema_version: str
    document_labels: frozenset[str]
    impact_sentiments: frozenset[str]
    event_types: frozenset[str]
    event_subtypes: dict[str, frozenset[str]]
    common_argument_fields: frozenset[str]
    event_argument_fields: dict[str, frozenset[str]]
    raw: JsonDict

    def allowed_subtypes(self, event_type: str) -> frozenset[str]:
        return self.event_subtypes.get(event_type, frozenset())

    def allowed_argument_fields(self, event_type: str) -> frozenset[str]:
        return self.common_argument_fields | self.event_argument_fields.get(event_type, frozenset())

    def compact_prompt_view(self) -> JsonDict:
        """Return a compact taxonomy shape that is small enough for teacher prompts."""
        event_types: JsonDict = {}
        for event_type, config in self.raw["event_types"].items():
            if not isinstance(config, dict):
                continue
            event_types[event_type] = {
                "description": config.get("description", ""),
                "subtypes": list((config.get("subtypes") or {}).keys()),
                "argument_fields": config.get("argument_fields") or [],
            }
        return {
            "schema_version": self.schema_version,
            "document_labels": sorted(self.document_labels),
            "impact_sentiments": sorted(self.impact_sentiments),
            "common_argument_fields": sorted(self.common_argument_fields),
            "event_types": event_types,
        }


@lru_cache(maxsize=8)
def load_event_taxonomy(path: PathLike = DEFAULT_TAXONOMY_PATH) -> EventTaxonomy:
    taxonomy_path = resolve_project_path(path)
    data = json.loads(Path(taxonomy_path).read_text(encoding="utf-8"))
    event_types_config = data.get("event_types")
    if not isinstance(event_types_config, dict):
        raise ValueError(f"Taxonomy must contain event_types mapping: {taxonomy_path}")

    event_subtypes: dict[str, frozenset[str]] = {}
    event_argument_fields: dict[str, frozenset[str]] = {}
    for event_type, config in event_types_config.items():
        if not isinstance(config, dict):
            raise ValueError(f"Invalid taxonomy config for event type: {event_type}")
        subtypes = config.get("subtypes") or {}
        if not isinstance(subtypes, dict):
            raise ValueError(f"Subtypes must be a mapping for event type: {event_type}")
        argument_fields = config.get("argument_fields") or []
        if not isinstance(argument_fields, list):
            raise ValueError(f"argument_fields must be a list for event type: {event_type}")
        event_subtypes[event_type] = frozenset(str(item) for item in subtypes)
        event_argument_fields[event_type] = frozenset(str(item) for item in argument_fields)

    return EventTaxonomy(
        schema_version=str(data.get("schema_version") or "event_schema_v1"),
        document_labels=frozenset(str(item) for item in data.get("document_labels", [])),
        impact_sentiments=frozenset(str(item) for item in data.get("impact_sentiments", [])),
        event_types=frozenset(str(item) for item in event_types_config),
        event_subtypes=event_subtypes,
        common_argument_fields=frozenset(
            str(item) for item in data.get("common_argument_fields", [])
        ),
        event_argument_fields=event_argument_fields,
        raw=data,
    )
