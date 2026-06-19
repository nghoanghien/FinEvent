"""Data ingestion package for collecting and cleaning financial articles."""

from finevent.ingestion.pipeline import run_local_html_ingestion

__all__ = ["run_local_html_ingestion"]
