from __future__ import annotations

from finevent.schema.validation import parse_teacher_output, validate_label_document

ARTICLE = {
    "article_id": "cafef_833adef5f3d9",
    "source": "cafef",
    "url": "file://tests/fixtures/html/cafef_sample.html",
    "title": "HPG khoi cong du an nha may moi",
    "published_at": "2026-01-15T08:00:00+07:00",
    "text": (
        "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.\n"
        "Du an du kien mo rong nang luc san xuat va co the tac dong tich cuc "
        "den ket qua kinh doanh."
    ),
    "tickers_hint": ["HPG"],
    "company_names_hint": ["Hoa Phat Group"],
}


def valid_label() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
        "document_label": "HAS_EVENT",
        "events": [
            {
                "event_id": "cafef_833adef5f3d9_e01",
                "ticker": "HPG",
                "company_name": "Hoa Phat Group",
                "event_type": "EXPANSION",
                "event_subtype": "NEW_FACTORY",
                "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
                "event_arguments": {
                    "project": "du an nha may moi",
                    "location": "khu cong nghiep",
                },
                "impact_sentiment": "POSITIVE",
                "evidence_span": (
                    "Tap doan Hoa Phat cong bo khoi cong du an nha may moi "
                    "tai khu cong nghiep."
                ),
                "source_url": "file://tests/fixtures/html/cafef_sample.html",
                "published_at": "2026-01-15T08:00:00+07:00",
                "confidence": 0.86,
            }
        ],
        "warnings": [],
        "model_info": {
            "model_name": "fixture_teacher",
            "prompt_version": "m02_teacher_v1",
            "run_id": "fixture_run",
        },
    }


def test_valid_label_passes() -> None:
    result = validate_label_document(valid_label(), ARTICLE)

    assert result.is_valid
    assert result.normalized is not None
    assert result.normalized["events"][0]["event_type"] == "EXPANSION"


def test_fenced_teacher_output_can_be_parsed() -> None:
    parsed = parse_teacher_output('```json\n{"article_id":"a","events":[]}\n```')

    assert parsed == {"article_id": "a", "events": []}


def test_invalid_event_type_is_rejected() -> None:
    label = valid_label()
    label["events"][0]["event_type"] = "BAD_TYPE"

    result = validate_label_document(label, ARTICLE)

    assert not result.is_valid
    assert any(issue.code == "invalid_event_type" for issue in result.errors)


def test_invalid_subtype_for_event_type_is_rejected() -> None:
    label = valid_label()
    label["events"][0]["event_subtype"] = "BIDDING_WIN"

    result = validate_label_document(label, ARTICLE)

    assert not result.is_valid
    assert any(issue.code == "invalid_event_subtype_for_type" for issue in result.errors)


def test_missing_evidence_is_rejected() -> None:
    label = valid_label()
    label["events"][0]["evidence_span"] = "Cong ty cong bo mot su kien khong he nam trong bai viet."

    result = validate_label_document(label, ARTICLE)

    assert not result.is_valid
    assert any(issue.code == "evidence_not_grounded" for issue in result.errors)


def test_no_event_requires_empty_events() -> None:
    label = valid_label()
    label["document_label"] = "NO_EVENT"

    result = validate_label_document(label, ARTICLE)

    assert not result.is_valid
    assert any(issue.code == "no_event_has_events" for issue in result.errors)
