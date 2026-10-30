"""Synthetic segmentation probe only; no product code, DB, network, or LLM.

Pair labels are fixture truth. Co-location measures context preservation, not
semantic detection. The follow-up join is an oracle using explicit reply IDs.
"""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path


def fixture(days):
    start = datetime(2026, 10, 23, 9, tzinfo=UTC)
    rows = []
    for day in range(days):
        for pos in range(300):
            stamp = start + timedelta(days=day, minutes=(pos // 75) * 70, seconds=(pos % 75) * 20)
            rows.append(
                {
                    "id": f"M{len(rows) + 1:05}",
                    "time": stamp,
                    "sender": pos % 2,
                    "text": "匿名日常消息🙂",
                    "reply_to": None,
                }
            )
    pairs = []
    for day in range(days):
        base = day * 300
        for left, right in [(44, 45), (149, 150), (199, 200)]:
            pairs.append((base + left, base + right))
        if day + 1 < days:
            pairs.append((base + 299, base + 300))
    pairs.append((10, len(rows) - 5))
    for number, (left, right) in enumerate(pairs):
        rows[left]["text"] = f"事件{number}：我有些难过，希望被听见。"
        rows[right]["text"] = f"回应事件{number}：我听到了，我们再谈谈。"
        rows[right]["reply_to"] = rows[left]["id"]
    return rows, pairs


def fixed(rows):
    return [list(range(i, min(i + 200, len(rows)))) for i in range(0, len(rows), 200)]


def temporal(rows):
    buckets = {}
    for i, row in enumerate(rows):
        buckets.setdefault(int(row["time"].timestamp()) // 900, []).append(i)
    return [part[i : i + 200] for part in buckets.values() for i in range(0, len(part), 200)]


def episodes(rows):
    sessions = [[]]
    for i, row in enumerate(rows):
        if i and row["time"] - rows[i - 1]["time"] > timedelta(minutes=30):
            sessions.append([])
        sessions[-1].append(i)
    cores, current = [], []
    for session in sessions:
        for offset in range(0, len(session), 200):
            piece = session[offset : offset + 200]
            if len(current) + len(piece) > 200:
                cores.append(current)
                current = []
            current += piece
    if current:
        cores.append(current)
    return cores


def evaluate(rows, pairs, cores, overlap):
    seen = Counter(i for core in cores for i in core)
    assert set(seen) == set(range(len(rows))) and all(v == 1 for v in seen.values())
    windows = [
        set(range(max(0, core[0] - overlap), min(len(rows), core[-1] + overlap + 1)))
        for core in cores
    ]
    colocated = sum(any(a in window and b in window for window in windows) for a, b in pairs)
    appearances = sum(len(window) for window in windows)
    wire_bytes = sum(
        len(
            json.dumps(
                [
                    {
                        "id": rows[i]["id"],
                        "sender": rows[i]["sender"],
                        "text": rows[i]["text"],
                        "reply_to": rows[i]["reply_to"],
                    }
                    for i in sorted(window)
                ],
                ensure_ascii=False,
            ).encode()
        )
        for window in windows
    )
    return {
        "chunks": len(cores),
        "unique_core_messages": len(seen),
        "context_appearances": appearances,
        "overlap_appearances": appearances - len(rows),
        "pair_colocation": colocated,
        "pair_total": len(pairs),
        "wire_bytes_one_pass": wire_bytes,
        "largest_core_text_bytes": max(
            sum(len(rows[i]["text"].encode()) for i in core) for core in cores
        ),
    }


def run():
    result = {"kind": "synthetic_structural_probe_v1", "provider_calls": 0, "cases": []}
    for days in [3, 7]:
        rows, pairs = fixture(days)
        policies = [
            ("fixed_200", fixed(rows), 0),
            ("time_15min", temporal(rows), 0),
            ("session_pack_200", episodes(rows), 0),
            ("session_pack_halo20", episodes(rows), 20),
        ]
        measures = {name: evaluate(rows, pairs, cores, halo) for name, cores, halo in policies}
        # Explicit links test provenance reachability; they are not LLM detections.
        lookup = {row["id"]: row for row in rows}
        linked = {(row["reply_to"], row["id"]) for row in rows if row["reply_to"] in lookup}
        assert all((rows[a]["id"], rows[b]["id"]) in linked for a, b in pairs)
        raw_hits = sum(
            a in range(max(0, core[0] - 20), min(len(rows), core[-1] + 21))
            for a, _ in pairs
            for core in episodes(rows)
        )
        dedup = {(rows[a]["id"], rows[b]["id"]) for a, b in pairs}
        k = len(episodes(rows))
        result["cases"].append(
            {
                "days": days,
                "messages": len(rows),
                "policies": measures,
                "oracle_followup_pairs": len(linked),
                "candidate_appearances_with_halo": raw_hits,
                "unique_events_by_anchor_ids": len(dedup),
                "illustrative_calls_upper_3K_plus_8": 3 * k + 8,
                "illustrative_reserved_tokens_at_128KiB_per_call": (3 * k + 8)
                * (131072 + 4096 + 4096),
            }
        )
    # Exact IDs preserve identical text; forged IDs and out-of-scope follow-ups fail membership.
    assert rows[5]["text"] == rows[6]["text"] and rows[5]["id"] != rows[6]["id"]
    assert "foreign-M00001" not in lookup
    assert rows[-5]["id"] not in {row["id"] for row in rows[:200]}
    result["source_hash_normalization"] = "utf8-universal-newlines"
    result["source_sha256"] = hashlib.sha256(
        Path(__file__).read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
