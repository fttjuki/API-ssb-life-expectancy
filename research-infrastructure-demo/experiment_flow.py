"""Simulate consent-gated randomization using synthetic invitee records."""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "synthetic_recruitment.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "experiment_summary.json"
DEFAULT_RESPONSES = ROOT / "outputs" / "experiment_synthetic_responses.csv"
MIN_CELL_SIZE = 5


def read_invitees(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def run_experiment_flow(
    invitees: Iterable[dict[str, str]], seed: int = 2026
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Consent-gate, randomize, and simulate outcomes; never uses real people."""
    seen_codes: set[str] = set()
    consented: list[str] = []
    invited_count = 0

    for row_number, row in enumerate(invitees, start=2):
        invited_count += 1
        if not {"invitee_code", "consent"}.issubset(row):
            raise ValueError(f"Row {row_number} is missing required fields")
        code = row["invitee_code"].strip()
        consent = row["consent"].strip().lower()
        if not code or code in seen_codes:
            raise ValueError(f"Row {row_number} has a missing or duplicate invitee code")
        if consent not in {"yes", "no"}:
            raise ValueError(f"Row {row_number} has an invalid consent value")
        seen_codes.add(code)
        if consent == "yes":
            consented.append(code)

    rng = random.Random(seed)
    rng.shuffle(consented)
    assignments = ["control" if index % 2 == 0 else "intervention" for index in range(len(consented))]
    rng.shuffle(assignments)

    responses: list[dict[str, object]] = []
    for index, (arm, _invitee_code) in enumerate(zip(assignments, consented), start=1):
        responses.append({
            "synthetic_participant_code": f"SYN-{index:03d}",
            "assigned_arm": arm,
            "synthetic_score": rng.randint(1, 5),
        })

    by_arm: dict[str, list[int]] = defaultdict(list)
    for response in responses:
        by_arm[str(response["assigned_arm"])].append(int(response["synthetic_score"]))

    arm_summary: dict[str, object] = {}
    for arm in ("control", "intervention"):
        scores = by_arm[arm]
        arm_summary[arm] = (
            {"n": len(scores), "mean_score": round(sum(scores) / len(scores), 2)}
            if len(scores) >= MIN_CELL_SIZE
            else "suppressed"
        )

    summary: dict[str, object] = {
        "invitees": invited_count,
        "consented": len(consented),
        "not_consented": invited_count - len(consented),
        "randomized": len(responses),
        "groups": arm_summary,
        "small_cell_suppression_threshold": MIN_CELL_SIZE,
        "seed": seed,
    }
    return responses, summary


def main() -> None:
    invitees = read_invitees(DEFAULT_INPUT)
    responses, summary = run_experiment_flow(invitees)
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with DEFAULT_RESPONSES.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=["synthetic_participant_code", "assigned_arm", "synthetic_score"])
        writer.writeheader()
        writer.writerows(responses)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
