import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from air_traffic_beam.collectors import aircraft_states as collector
from air_traffic_beam.exceptions import OpenSkyConfigurationError


@pytest.fixture
def collection_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "bronze"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "collector",
            "--max-collections=2",
            "--interval-seconds=1",
            f"--output={output}",
        ],
    )
    return output


def test_collection_writes_batch_and_report(collection_output, mocker):
    response = {"time": 1710000010, "states": [["aabbcc"]]}
    fetch = mocker.patch.object(
        collector.OpenSkyClient, "get_states", return_value=response
    )
    sleep = mocker.patch.object(collector.time, "sleep")

    report = json.loads(Path(collector.run()).read_text())

    files = list(collection_output.rglob("*.jsonl"))
    assert len(files) == 1
    records = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert [record["payload"] for record in records] == [response, response]
    assert [record["_metadata"]["collection_number"] for record in records] == [1, 2]
    assert (
        records[0]["_metadata"]["execution_id"]
        == records[1]["_metadata"]["execution_id"]
    )
    assert report["output_records"] == 2
    assert report["output_paths"] == [str(files[0])]
    assert fetch.call_count == 2
    sleep.assert_called_once_with(1)


@pytest.mark.parametrize("partial", [False, True])
def test_collection_failure_preserves_received_data(collection_output, mocker, partial):
    response = {"time": 1710000010, "states": [["aabbcc"]]}
    failure = RuntimeError("API unavailable")
    mocker.patch.object(
        collector.OpenSkyClient,
        "get_states",
        side_effect=[response, failure] if partial else [failure],
    )
    mocker.patch.object(collector.time, "sleep")
    report_writer = mocker.spy(collector, "write_run_report")

    with pytest.raises(RuntimeError, match="API unavailable"):
        collector.run()

    report = json.loads(Path(report_writer.spy_return).read_text())
    assert report["status"] == "failed"
    assert report["error_message"] == "API unavailable"
    assert report["output_records"] == int(partial)
    files = list(collection_output.rglob("*.jsonl"))
    assert len(files) == int(partial)
    if partial:
        assert files[0].name.endswith("_partial.jsonl")
        assert json.loads(files[0].read_text())["payload"] == response
    else:
        assert report["output_paths"] == []


def test_atomic_write_failure_preserves_existing_file(tmp_path):
    output = tmp_path / "batch.jsonl"
    output.write_text('{"original": true}\n')

    with pytest.raises(TypeError):
        collector.write_jsonl_atomic(output, [{"valid": True}, {"invalid": object()}])

    assert json.loads(output.read_text()) == {"original": True}
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize(
    "bounds",
    [
        (1, 1, -47, -45),
        (-24, -23, -45, -47),
        (-91, -23, -47, -45),
        (-24, -23, -181, -45),
    ],
)
def test_invalid_bounds_are_rejected(bounds):
    lat_min, lat_max, lon_min, lon_max = bounds
    with pytest.raises(OpenSkyConfigurationError):
        collector._validate_bounds(
            Namespace(
                lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max
            )
        )
