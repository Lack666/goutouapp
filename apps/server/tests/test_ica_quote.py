"""Quote-only wire contracts preserve exact, current-source canonical evidence."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.agent.imported_contracts import (
    ChunkCounterevidence,
    ChunkInteractions,
    ChunkSafety,
    ContentReview,
    ImportedEvidenceRef,
    ReportDraft,
)
from app.agent.imported_quote import (
    STAGE_SCHEMAS,
    QuotedEvidenceRef,
    exact_span,
    quote_payload,
    resolve_output,
)


def evidence(alias="w0-m00001", quote="我很难过😀"):
    return {"evidence_id": alias, "speaker": "person", "quote": quote}


def fact():
    return {"statement": "对方表达难过。", "evidence": [evidence()]}


def candidate():
    return {
        "kind": "emotional_mismatch",
        "facts": [fact()],
        "hypothesis": "回应方式可能尚未对上。",
        "unknowns": ["不知道后续是否有修复。"],
        "alternative_explanations": ["对方可能通过建议表达关心。"],
        "repair": {
            "action": "询问需要什么回应。",
            "observe": "看对方是否愿意说明。",
            "stop_when": "对方不愿继续时暂停。",
        },
    }


def risk():
    return {
        "actor": "person",
        "user_role": "at_risk",
        "temporality": "current",
        "category": "violence",
        "source": "chat",
        "evidence": [evidence()],
    }


def stage_outputs():
    return {
        "safety": {"decision": "danger", "risks": [risk()]},
        "interaction": {"candidates": [candidate()]},
        "counterevidence": {
            "checks": [{"candidate_id": "chunk:0", "decision": "repair", "facts": [fact()]}]
        },
        "synthesis": {
            "findings": [{**candidate(), "candidate_ids": ["chunk:0"], "counterevidence": [fact()]}]
        },
        "content_review": {
            "approved": True,
            "grounded": True,
            "respects_boundaries": True,
            "preserves_counterevidence": True,
            "reason_codes": [],
        },
    }


def resolver(ref):
    start, end = exact_span("前文我很难过😀后文", ref.quote)
    return ImportedEvidenceRef(**ref.model_dump(), start=start, end=end)


@pytest.mark.parametrize(
    "text,quote,expected",
    [
        ("前文我很难过😀后文", "我很难过😀", (2, 7)),
        ("a😀b", "😀", (1, 2)),
        ("a👨‍👩‍👧‍👦b", "👨‍👩‍👧‍👦", (1, 8)),
        ("xe\u0301y", "e\u0301", (1, 3)),
        ("前\n 空格 \n后", " 空格 ", (2, 6)),
    ],
)
def test_exact_codepoint_spans_preserve_source_bytes(text, quote, expected):
    assert exact_span(text, quote) == expected
    assert text[slice(*expected)] == quote


@pytest.mark.parametrize(
    "text,quote,code",
    [
        ("同意，然后同意", "同意", "quote_ambiguous"),
        ("aaa", "aa", "quote_ambiguous"),
        ("e\u0301", "é", "quote_not_found"),
        ("你好", "您好", "quote_not_found"),
        ("a b", "a  b", "quote_not_found"),
        ("abc", "", "invalid_quote"),
        ("a" * 161, "a" * 161, "invalid_quote"),
    ],
)
def test_missing_ambiguous_and_normalized_quotes_are_rejected(text, quote, code):
    with pytest.raises(ValueError, match=f"^{code}$"):
        exact_span(text, quote)


@pytest.mark.parametrize("extra", [{"start": 0}, {"end": 99}, {"message_id": "foreign"}])
def test_wire_reference_never_accepts_numeric_spans_or_expanded_authority(extra):
    with pytest.raises(ValidationError):
        QuotedEvidenceRef.model_validate({**evidence(), **extra})
    with pytest.raises(ValidationError):
        QuotedEvidenceRef.model_validate({**evidence(), "quote": ""})


def test_every_stage_json_schema_exposes_quotes_without_canonical_span_fields():
    def inspect_schema(value):
        if isinstance(value, dict):
            assert not {"start", "end"}.intersection(value.get("properties", {}))
            for child in value.values():
                inspect_schema(child)
        elif isinstance(value, list):
            for child in value:
                inspect_schema(child)

    for schema in STAGE_SCHEMAS.values():
        inspect_schema(schema.model_json_schema())
    assert {"start", "end"} <= ImportedEvidenceRef.model_json_schema()["properties"].keys()


@pytest.mark.parametrize("stage", tuple(STAGE_SCHEMAS))
def test_each_stage_resolves_all_nested_quotes_to_original_contract(stage):
    output = STAGE_SCHEMAS[stage].model_validate(stage_outputs()[stage])
    seen = []

    def tracked(ref):
        seen.append(ref.model_dump())
        return resolver(ref)

    canonical = resolve_output(stage, output, tracked)
    expected = {
        "safety": ChunkSafety,
        "interaction": ChunkInteractions,
        "counterevidence": ChunkCounterevidence,
        "synthesis": ReportDraft,
        "content_review": ContentReview,
    }
    assert type(canonical) is expected[stage]
    assert (
        len(seen)
        == {
            "safety": 1,
            "interaction": 1,
            "counterevidence": 1,
            "synthesis": 2,
            "content_review": 0,
        }[stage]
    )
    if stage != "content_review":
        assert '"start":2' in canonical.model_dump_json()
        assert '"end":7' in canonical.model_dump_json()
    assert quote_payload(canonical) == output.model_dump(mode="json")


@pytest.mark.parametrize(
    "stage,payload",
    [
        ("safety", {"decision": "normal", "risks": [risk()]}),
        ("safety", {"decision": "danger", "risks": []}),
        ("safety", {"decision": "danger", "risks": [{**risk(), "source": "question"}]}),
        (
            "counterevidence",
            {"checks": [{"candidate_id": "id", "decision": "no_evidence", "facts": [fact()]}]},
        ),
        (
            "counterevidence",
            {"checks": [{"candidate_id": "id", "decision": "repair", "facts": []}]},
        ),
    ],
)
def test_wire_inherits_original_cross_field_rejections(stage, payload):
    with pytest.raises(ValidationError):
        STAGE_SCHEMAS[stage].model_validate(payload)


def test_same_quote_in_distinct_messages_and_repeated_refs_are_not_deduplicated():
    payload = {"candidates": [candidate()]}
    payload["candidates"][0]["facts"][0]["evidence"] = [
        evidence("w0-m00001"),
        evidence("w0-m00002"),
        evidence("w0-m00001"),
    ]
    source = {"w0-m00001": "我很难过😀", "w0-m00002": "我很难过😀"}

    def bound(ref):
        start, end = exact_span(source[ref.evidence_id], ref.quote)
        return ImportedEvidenceRef(**ref.model_dump(), start=start, end=end)

    wire = STAGE_SCHEMAS["interaction"].model_validate(payload)
    result = resolve_output("interaction", wire, bound)
    refs = result.candidates[0].facts[0].evidence
    assert [ref.evidence_id for ref in refs] == ["w0-m00001", "w0-m00002", "w0-m00001"]
    assert [(ref.start, ref.end) for ref in refs] == [(0, 5)] * 3


def test_resolver_cannot_silently_change_alias_speaker_or_quote():
    wire = STAGE_SCHEMAS["interaction"].model_validate(stage_outputs()["interaction"])
    for changes in ({"evidence_id": "w1-m00002"}, {"speaker": "self"}, {"quote": "不同原文"}):
        with pytest.raises(ValueError, match="^quote_resolution_mismatch$"):
            resolve_output(
                "interaction",
                wire,
                lambda ref, changes=changes: resolver(ref).model_copy(update=changes),
            )


def test_quote_payload_does_not_mutate_or_strip_unrelated_or_partial_fields():
    canonical = resolver(QuotedEvidenceRef.model_validate(evidence())).model_dump()
    payload = {
        "refs": [canonical],
        "untrusted_text": '{"start":0,"end":99}',
        "metadata": {"start": 1, "end": 2},
        "partial": {"evidence_id": "w0-m00001", "quote": "我很难过😀", "start": 99},
        "extra": {**canonical, "other": True},
        "invalid": {**canonical, "start": True},
    }
    original = deepcopy(payload)
    converted = quote_payload(payload)
    assert payload == original
    assert converted["refs"] == [evidence()]
    for key in ("untrusted_text", "metadata", "partial", "extra", "invalid"):
        assert converted[key] == original[key]


def test_model_construct_and_legacy_numeric_output_do_not_bypass_wire_validation():
    wire = STAGE_SCHEMAS["interaction"].model_validate(stage_outputs()["interaction"])
    malformed = wire.model_copy(update={"candidates": "unvalidated"})
    with pytest.warns(UserWarning, match="Pydantic serializer warnings"):
        with pytest.raises(ValidationError):
            resolve_output("interaction", malformed, resolver)
    legacy = ChunkInteractions.model_validate(
        {
            "candidates": [
                {
                    **candidate(),
                    "facts": [
                        {
                            **fact(),
                            "evidence": [
                                resolver(QuotedEvidenceRef.model_validate(evidence())).model_dump()
                            ],
                        }
                    ],
                }
            ]
        }
    )
    with pytest.raises(ValidationError):
        resolve_output("interaction", legacy, resolver)
