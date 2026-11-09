"""Migration-only replay of fixed synthetic v1 outputs; never send or invent a model call."""

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from app.agent.imported_analysis import ImportedAnalysisError, ImportedAnalysisRuntime
from app.chat_import.analysis_scope import validate_evidence
from evals.ica.runner import case_to_contexts, load_cases

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "docs/evidence/ica-bq/batch-v1/calls.jsonl": (
        "be80cb9902d62d81e1e3a2c98365efea40b3505f92f447822110eb84dbbd5f15"
    ),
    "docs/evidence/ica-bq/batch-v1/results.jsonl": (
        "3f6aa49c5b1b6307721d95ffcdfdb9cd7b42b18938d84b10880e50e84a5db729"
    ),
    "evals/ica/v1/cases.jsonl": (
        "f08f5d4529c6c3b7a3794215c50c7c20a34c2d9ae376e7d34603e23a5ce3aae2"
    ),
}
LEGACY_FIELDS = {"evidence_id", "speaker", "start", "end", "quote"}


def migrate_quotes(value):
    """Only the five-field v1 evidence object loses numeric offsets; other values stay literal."""
    if isinstance(value, list):
        return [migrate_quotes(item) for item in value]
    if isinstance(value, dict):
        keys = (
            [key for key in value if key not in {"start", "end"}]
            if set(value) == LEGACY_FIELDS
            else value
        )
        return {key: migrate_quotes(value[key]) for key in keys}
    return value


def migrated_json(output):
    return json.dumps(
        migrate_quotes(json.loads(output)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def legacy_refs(value, path=()):
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from legacy_refs(item, (*path, index))
    elif isinstance(value, dict):
        if set(value) == LEGACY_FIELDS:
            yield path, value
        else:
            for key, item in value.items():
                yield from legacy_refs(item, (*path, key))


def bindings(contexts):
    aliases, chunks = {}, {}
    for window_index, context in enumerate(contexts):
        for message in context.messages:
            aliases[f"w{window_index}-m{len(aliases) + 1:05d}"] = context, message
        for chunk in context.chunks:
            chunks[chunk.id] = set(chunk.core + chunk.halo_before + chunk.halo_after)
    return aliases, chunks


def audit_output(contexts, admission, value):
    """Count source-exact local quotes, not successful stages or correct interpretations."""
    from app.agent.imported_quote import exact_span

    aliases, chunks = bindings(contexts)
    chunk_id = admission.get("chunk_id")
    details = []
    for path, ref in legacy_refs(value):
        item = {
            "path": list(path),
            "evidence_id": ref["evidence_id"],
            "old_span": [ref["start"], ref["end"]],
            "accepted": False,
        }
        details.append(item)
        if ref["evidence_id"] not in aliases:
            item["reason"] = "unknown_alias"
            continue
        context, message = aliases[ref["evidence_id"]]
        if chunk_id is not None and message.id not in chunks.get(chunk_id, set()):
            item["reason"] = "outside_recorded_chunk"
            continue
        if message.speaker != ref["speaker"]:
            item["reason"] = "wrong_speaker"
            continue
        try:
            start, end = exact_span(message.content, ref["quote"])
            validate_evidence(context, message.id, start, end, ref["quote"])
        except (ValueError, TypeError):
            item["reason"] = "quote_missing_or_ambiguous"
            continue
        old_span_valid = False
        if type(ref["start"]) is int and type(ref["end"]) is int:
            try:
                validate_evidence(context, message.id, ref["start"], ref["end"], ref["quote"])
                old_span_valid = True
            except ValueError:
                pass
        item.update(
            accepted=True,
            message_id=str(message.id),
            new_span=[start, end],
            old_span_valid=old_span_valid,
        )
    return details


def load_recordings():
    for relative, expected in SOURCES.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("fixed_recording_hash_mismatch")
    events = [
        json.loads(line)
        for line in (ROOT / next(iter(SOURCES))).read_text(encoding="utf-8").splitlines()
    ]
    results = [
        json.loads(line)
        for line in (ROOT / list(SOURCES)[1]).read_text(encoding="utf-8").splitlines()
    ]
    returned = {}
    for event in events:
        if event["status"] == "returned":
            if event["call_id"] in returned:
                raise ValueError("duplicate_returned_recording")
            returned[event["call_id"]] = event["synthetic_visible_output"]
    grouped = {(row["case_id"], row["arm"]): [] for row in results}
    if len(grouped) != 64:
        raise ValueError("fixed_recording_inventory_mismatch")
    for event in events:
        if event["status"] != "admitted" or event.get("arm") not in {"event", "baseline"}:
            continue
        key = event["case_id"], event["arm"]
        if key not in grouped or event["call_id"] not in returned:
            raise ValueError("missing_recorded_output")
        grouped[key].append({**event, "visible_output": returned[event["call_id"]]})
    return results, grouped


class RecordingUnavailable(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class RecordedOnlyProvider:
    """Consume one actual recording per matching stage; no fabricated continuation exists."""

    def __init__(self, sequence):
        self.sequence, self.cursor, self.attempts = sequence, 0, []
        self.pending = None

    async def before(self, stage, chunk_id, messages, schema):
        entry = {
            "stage": stage,
            "chunk_id": chunk_id,
            "schema": schema.__name__,
            "status": "not_recorded",
            "recorded_call_id": None,
        }
        self.attempts.append(entry)
        if self.cursor >= len(self.sequence):
            raise RecordingUnavailable("recording_exhausted")
        record = self.sequence[self.cursor]
        if (stage, chunk_id) != (record["stage"], record.get("chunk_id")):
            raise RecordingUnavailable("recording_stage_or_chunk_mismatch")
        entry.update(status="recorded", recorded_call_id=record["call_id"])
        self.pending = record
        return str(record["call_id"])

    async def structured_output(self, messages, schema, *, model=None, temperature=None):
        if self.pending is None:
            raise RecordingUnavailable("recording_not_selected")
        record, self.pending = self.pending, None
        self.cursor += 1
        return schema.model_validate_json(migrated_json(record["visible_output"]))

    async def after(self, call_id, output, error):
        entry = self.attempts[-1]
        if str(entry["recorded_call_id"]) != call_id:
            raise RecordingUnavailable("recording_receipt_mismatch")
        entry.update(status="rejected" if error else "validated", error_code=error)


async def replay_recording(case, arm, sequence):
    contexts = case_to_contexts(case)
    provider = RecordedOnlyProvider(sequence)
    row = {
        "case_id": case["case_id"],
        "arm": arm,
        "migration_only": True,
        "external_provider_calls": 0,
        "report": None,
        "status": None,
        "error_code": None,
        "incomplete_recording": False,
        "attempts": provider.attempts,
        "recorded_stages_available": len(sequence),
        "recorded_output_hashes": [
            {
                "recorded_call_id": record["call_id"],
                "original_sha256": hashlib.sha256(record["visible_output"].encode()).hexdigest(),
                "migrated_sha256": hashlib.sha256(
                    migrated_json(record["visible_output"]).encode()
                ).hexdigest(),
            }
            for record in sequence
        ],
    }
    try:
        await ImportedAnalysisRuntime(provider, evidence_protocol="quote-v2").run(
            contexts, case["question"], "recorded-only", provider.before, provider.after
        )
        if provider.cursor != len(sequence):
            raise RecordingUnavailable("recording_has_unused_stages")
        row["status"] = "all_recorded_stages_validated"
    except RecordingUnavailable as error:
        row.update(status="recording_incomplete", incomplete_recording=True, error_code=error.code)
    except ImportedAnalysisError as error:
        row.update(status="validation_rejected", error_code=error.code)
    row["recorded_stages_consumed"] = provider.cursor
    return row


async def run_replays():
    original_results, grouped = load_recordings()
    cases = {case["case_id"]: case for case in load_cases("holdout")}
    rows, details = [], []
    for original in original_results:
        key = original["case_id"], original["arm"]
        case, sequence = cases[key[0]], grouped[key]
        contexts = case_to_contexts(case)
        for record in sequence:
            try:
                value = json.loads(record["visible_output"])
            except (ValueError, TypeError):
                continue
            for item in audit_output(contexts, record, value):
                details.append(
                    {
                        "case_id": key[0],
                        "arm": key[1],
                        "recorded_call_id": record["call_id"],
                        **item,
                    }
                )
        rows.append(await replay_recording(case, key[1], sequence))
    stats = Counter(row["status"] for row in rows)
    return {
        "version": "ica-quote-migration-replay-v1",
        "migration": "Remove only v1 numeric offsets; retain all other recorded fields verbatim.",
        "source_sha256": SOURCES,
        "external_provider_calls": 0,
        "rows": rows,
        "reference_details": details,
        "summary": {
            "recordings": len(rows),
            "recording_statuses": dict(stats),
            "references": len(details),
            "source_exact_unique_quotes": sum(item["accepted"] for item in details),
            "old_invalid_span_resolved": sum(
                item["accepted"] and not item["old_span_valid"] for item in details
            ),
            "rejected_quotes": sum(not item["accepted"] for item in details),
        },
        "limitations": [
            "This is migration-only reuse of old visible synthetic outputs, not new inference.",
            "Missing later stages are never synthesized; all report fields stay null.",
            "No new model completion rate, semantic quality, SQL authority or blind-test pass.",
            "Old known diagnostic cases require replacement for independent acceptance.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run_replays())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
