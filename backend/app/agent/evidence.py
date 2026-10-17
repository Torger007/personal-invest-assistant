"""Select immutable, bounded evidence from one constrained Agent run."""
from __future__ import annotations

from typing import Any, Iterable

from app.agent.contracts import EvidenceSnapshot


MAX_SAVED_EVIDENCE = 1500


def collect_evidence_candidates(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep compact facts, never the raw tool payload or free-text tool output."""
    collected: dict[str, dict[str, Any]] = {}
    for item in results:
        for raw in item.get("result", {}).get("evidence", []):
            fact = EvidenceSnapshot.model_validate(raw).model_dump(mode="json")
            evidence_id = fact["evidence_id"]
            if evidence_id in collected:
                raise ValueError(f"duplicate evidence_id: {evidence_id}")
            if len(collected) >= MAX_SAVED_EVIDENCE:
                raise ValueError("evidence snapshot exceeds bounded storage")
            collected[evidence_id] = fact
    return list(collected.values())


def select_evidence_snapshot(
    results: Iterable[dict[str, Any]], evidence_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Persist only facts cited by a structured report, rejecting stale IDs."""
    return select_saved_evidence_snapshot(collect_evidence_candidates(results), evidence_ids)


def select_saved_evidence_snapshot(
    facts: Iterable[dict[str, Any]], evidence_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Select cited saved facts and their complete dependency closure."""
    available: dict[str, dict[str, Any]] = {}
    for raw in facts:
        item = EvidenceSnapshot.model_validate(raw).model_dump(mode="json")
        if item["evidence_id"] in available:
            raise ValueError(f"duplicate evidence_id: {item['evidence_id']}")
        available[item["evidence_id"]] = item
    requested = list(dict.fromkeys(evidence_ids))
    selected: list[dict[str, Any]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def include(evidence_id: str) -> None:
        if evidence_id not in available:
            raise ValueError(f"unknown evidence IDs: {evidence_id}")
        if evidence_id in visiting:
            raise ValueError("cyclic evidence dependencies")
        if evidence_id in visited:
            return
        visiting.add(evidence_id)
        fact = available[evidence_id]
        for dependency in fact["depends_on_evidence_ids"]:
            include(dependency)
        visiting.remove(evidence_id)
        visited.add(evidence_id)
        selected.append(fact)

    for evidence_id in requested:
        include(evidence_id)
    return selected
