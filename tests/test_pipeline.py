import json
import sys
from pathlib import Path
from unittest import mock

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssb_life.api import build_params, fetch_table, jsonstat_to_dataframe  # noqa: E402
from ssb_life.clean import clean_life_expectancy, sex_gap  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "05375_sample.json"


@pytest.fixture
def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_params_joins_codes():
    params = build_params({"Kjonn": ["1", "2"], "Tid": "*"})
    assert params["valueCodes[Kjonn]"] == "1,2"
    assert params["valueCodes[Tid]"] == "*"
    assert params["outputformat"] == "json-stat2"


def test_jsonstat_shape_and_order(sample):
    df = jsonstat_to_dataframe(sample)
    assert len(df) == 2 * 2 * 1 * 11
    # Last dimension (Tid) varies fastest: first row is men, age 0, 2015
    first = df.iloc[0]
    assert (first["Kjonn_code"], first["Alder_code"], first["Tid_code"]) == ("1", "000", "2015")
    assert first["value"] == 80.36
    # Women, age 65, 2025 is the very last value in SSB's response
    last = df.iloc[-1]
    assert (last["Kjonn_code"], last["Alder_code"], last["Tid_code"]) == ("2", "065", "2025")
    assert last["value"] == 21.91


def test_jsonstat_sparse_values(sample):
    sample["value"] = {"0": 80.36}
    df = jsonstat_to_dataframe(sample)
    assert df["value"].iloc[0] == 80.36
    assert df["value"].iloc[1:].isna().all()


def test_jsonstat_rejects_wrong_length(sample):
    sample["value"] = sample["value"][:-1]
    with pytest.raises(ValueError):
        jsonstat_to_dataframe(sample)


def test_clean_types_and_gap(sample):
    df = clean_life_expectancy(jsonstat_to_dataframe(sample))
    assert list(df.columns) == ["year", "sex", "age", "life_expectancy"]
    assert set(df["sex"]) == {"Men", "Women"}
    assert set(df["age"]) == {0, 65}
    gap = sex_gap(df)
    gap_2025 = gap.query("year == 2025 and age == 0")["gap_women_minus_men"].item()
    assert gap_2025 == pytest.approx(84.85 - 81.61)


def test_clean_rejects_impossible_values(sample):
    sample["value"][0] = 150
    with pytest.raises(ValueError):
        clean_life_expectancy(jsonstat_to_dataframe(sample))


def _response(status, payload=None):
    resp = mock.Mock(status_code=status)
    resp.json.return_value = payload
    resp.raise_for_status.side_effect = requests.HTTPError(str(status))
    return resp


def test_fetch_retries_on_rate_limit(sample):
    calls = [_response(429), _response(200, sample)]
    with mock.patch("ssb_life.api.requests.get", side_effect=calls) as get, \
         mock.patch("ssb_life.api.time.sleep"):
        data = fetch_table("05375", {"Tid": "*"})
    assert data == sample
    assert get.call_count == 2


def test_fetch_does_not_retry_bad_request():
    with mock.patch("ssb_life.api.requests.get", return_value=_response(400)) as get, \
         mock.patch("ssb_life.api.time.sleep"):
        with pytest.raises(requests.HTTPError):
            fetch_table("05375", {"Tid": "nonsense"})
    assert get.call_count == 1
