"""Small client for Statistics Norway's PxWebApi v2.

Docs: https://www.ssb.no/en/api/pxwebapiv2

The data endpoint is a plain HTTP GET:
    https://data.ssb.no/api/pxwebapi/v2/tables/{table_id}/data
        ?lang=en
        &outputformat=json-stat2
        &valueCodes[<dimension>]=<code1>,<code2>   (or * for all)
"""

from __future__ import annotations

import itertools
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.ssb.no/api/pxwebapi/v2"
USER_AGENT = "ssb-life-expectancy/1.0 (research demo; github.com)"


def build_params(selection: dict[str, list[str] | str], lang: str = "en") -> dict[str, str]:
    """Turn {"Kjonn": ["1", "2"], "Tid": "*"} into PxWebApi query parameters."""
    params = {"lang": lang, "outputformat": "json-stat2"}
    for dimension, codes in selection.items():
        if isinstance(codes, (list, tuple)):
            codes = ",".join(codes)
        params[f"valueCodes[{dimension}]"] = codes
    return params


def fetch_table(
    table_id: str,
    selection: dict[str, list[str] | str],
    lang: str = "en",
    retries: int = 3,
    timeout: float = 30,
) -> dict:
    """Download one table from SSB and return the parsed JSON-stat2 response.

    Retries with a growing pause on timeouts, rate limiting (HTTP 429) and
    server errors (5xx). Other errors (e.g. 400 for a bad dimension code)
    are raised immediately, because retrying will not fix them.
    """
    url = f"{BASE_URL}/tables/{table_id}/data"
    params = build_params(selection, lang)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == retries:
                raise
        else:
            if response.status_code == 200:
                return response.json()
            retryable = response.status_code == 429 or response.status_code >= 500
            if not retryable or attempt == retries:
                response.raise_for_status()
        time.sleep(2 ** attempt)  # 2 s, 4 s, ...

    raise RuntimeError("unreachable")  # loop always returns or raises


def save_json(data: dict, path: Path) -> None:
    """Keep the raw API response so the analysis can be re-run offline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def jsonstat_to_dataframe(data: dict) -> pd.DataFrame:
    """Convert a JSON-stat2 dataset into a long (tidy) DataFrame.

    JSON-stat stores all numbers in one flat list ("value"). The order is
    row-major over the dimensions listed in "id": the LAST dimension changes
    fastest. So we build every combination of category codes in that order
    and pair it with the values.

    One output row per cell, with a code column and a label column for each
    dimension, plus "value".
    """
    dim_ids: list[str] = data["id"]
    sizes: list[int] = data["size"]

    codes_per_dim = []
    for dim_id, size in zip(dim_ids, sizes):
        index = data["dimension"][dim_id]["category"]["index"]
        # "index" may be a dict {code: position} or a list of codes
        codes = sorted(index, key=index.get) if isinstance(index, dict) else list(index)
        if len(codes) != size:
            raise ValueError(f"Dimension {dim_id}: expected {size} codes, got {len(codes)}")
        codes_per_dim.append(codes)

    n_cells = 1
    for size in sizes:
        n_cells *= size

    values = data["value"]
    if isinstance(values, dict):  # sparse form: {"position": value}
        values = [values.get(str(i)) for i in range(n_cells)]
    if len(values) != n_cells:
        raise ValueError(f"Expected {n_cells} values, got {len(values)}")

    rows = []
    for combo, value in zip(itertools.product(*codes_per_dim), values):
        row = {}
        for dim_id, code in zip(dim_ids, combo):
            labels = data["dimension"][dim_id]["category"].get("label", {})
            row[f"{dim_id}_code"] = code
            row[dim_id] = labels.get(code, code)
        row["value"] = value
        rows.append(row)

    return pd.DataFrame(rows)
