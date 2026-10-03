"""Synthetic research workflow with optional, privacy-conscious API sharing."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "synthetic_participants.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "summary.json"
DEFAULT_LOG = ROOT / "outputs" / "pipeline.jsonl"
REQUIRED_FIELDS = {"participant_id", "age", "study_arm", "completed"}
MIN_CELL_SIZE = 5


def read_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def validate_records(records: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    validated: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for line_number, row in enumerate(records, start=2):
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"Row {line_number} is missing required fields: {sorted(missing)}")

        participant_id = row["participant_id"].strip()
        if not participant_id or participant_id in seen_ids:
            raise ValueError(f"Row {line_number} has a missing or duplicate participant ID")
        seen_ids.add(participant_id)

        try:
            age = int(row["age"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Row {line_number} has an invalid age") from error
        if not 18 <= age <= 100:
            raise ValueError(f"Row {line_number} has an age outside 18–100")

        study_arm = row["study_arm"].strip()
        if not study_arm:
            raise ValueError(f"Row {line_number} has a missing study arm")
        completed = row["completed"].strip().lower()
        if completed not in {"true", "false"}:
            raise ValueError(f"Row {line_number} has an invalid completed value")

        validated.append({"age": age, "study_arm": study_arm, "completed": completed == "true"})

    if not validated:
        raise ValueError("Input contains no participant records")
    return validated


def build_summary(records: list[dict[str, object]], min_cell_size: int = MIN_CELL_SIZE) -> dict[str, object]:
    """Return aggregate statistics and suppress study-arm cells smaller than k."""
    arms = Counter(str(record["study_arm"]) for record in records)
    arm_counts: dict[str, int | str] = {
        arm: count if count >= min_cell_size else "suppressed"
        for arm, count in sorted(arms.items())
    }
    return {
        "record_count": len(records),
        "mean_age_years": round(sum(int(row["age"]) for row in records) / len(records), 1),
        "completion_rate": round(sum(bool(row["completed"]) for row in records) / len(records), 3),
        "study_arm_counts": arm_counts,
        "small_cell_suppression_threshold": min_cell_size,
    }


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_processing_log(path: Path, events: list[dict[str, object]]) -> None:
    """Write allowlisted event fields; never log record contents or secrets."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for event in events:
            target.write(json.dumps(event, sort_keys=True) + "\n")


def post_summary(
    summary: dict[str, object],
    api_url: str,
    api_key: str,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> int:
    if not api_url.startswith("https://"):
        raise ValueError("The external API URL must use HTTPS")
    if not api_key.strip() or api_key == "replace-me-locally":
        raise ValueError("Set a real API key in RESEARCH_API_KEY before sending")

    request = urllib.request.Request(
        api_url,
        data=json.dumps(summary).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=5) as response:
            return int(response.status)
    except urllib.error.URLError as error:
        raise RuntimeError("External API request failed") from error


def run_pipeline(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    log_path: Path = DEFAULT_LOG,
    send_summary: bool = False,
) -> dict[str, object]:
    events: list[dict[str, object]] = [{"step": "start"}]
    logging.info("Pipeline started")

    raw_records = read_records(input_path)
    events.append({"step": "input_loaded", "record_count": len(raw_records)})
    logging.info("Loaded %d synthetic records", len(raw_records))

    records = validate_records(raw_records)
    events.append({"step": "validation_passed", "record_count": len(records)})
    logging.info("Input validation passed")

    summary = build_summary(records)
    events.append({"step": "aggregated", "record_count": len(records)})
    write_json(output_path, summary)
    events.append({"step": "summary_written"})

    if send_summary:
        api_url = os.environ.get("RESEARCH_API_URL", "")
        api_key = os.environ.get("RESEARCH_API_KEY", "")
        status = post_summary(summary, api_url, api_key)
        events.append({"step": "external_api_sent", "http_status": status})
        logging.info("Aggregate summary sent to configured API (HTTP %s)", status)

    write_processing_log(log_path, events)
    logging.info("Summary and processing log written")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV input (synthetic data by default)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Aggregate JSON output path")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="Processing log path")
    parser.add_argument(
        "--send-summary",
        action="store_true",
        help="Explicitly send only the aggregate summary to the configured HTTPS API",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = run_pipeline(args.input, args.output, args.log, args.send_summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
