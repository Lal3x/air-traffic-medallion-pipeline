import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import apache_beam as beam
import pyarrow.parquet as pq
from apache_beam.testing.test_pipeline import TestPipeline as BeamTestPipeline
from apache_beam.testing.util import assert_that, equal_to

from air_traffic_beam.pipelines.bronze_to_silver import run
from air_traffic_beam.transforms.aircraft_states import (
    REJECTED_TAG,
    ParseEnvelope,
    ValidateAndNormalizeAircraftState,
    normalize_state_vector,
)

FIXTURE = Path(__file__).parent / "fixtures" / "opensky_states_response.json"


def test_valid_state_vectors_are_expanded_and_normalized():
    record = {
        "_metadata": {
            "source": "opensky_network",
            "execution_id": "exec-1",
            "collection_number": 1,
            "ingested_at": "2026-09-14T10:00:00-03:00",
            "bounding_box": {
                "lat_min": -24.2,
                "lon_min": -47.2,
                "lat_max": -22.7,
                "lon_max": -45.5,
            },
        },
        "payload": {
            "time": 1710000010,
            "states": [
                [
                    "aabbcc",
                    "SWA123 ",
                    "United States",
                    1710000000,
                    1710000005,
                    -46.6,
                    -23.5,
                    1000.0,
                    False,
                    120.0,
                    180.0,
                    1.0,
                    5.0,
                    None,
                    1100.0,
                    "1234",
                    False,
                    0,
                    1,
                ]
            ],
        },
    }

    with BeamTestPipeline() as pipeline:
        valid = (
            pipeline
            | beam.Create([json.dumps(record)])
            | beam.ParDo(ParseEnvelope()).with_outputs(REJECTED_TAG, main="valid")
        )
        assert_that(
            valid.valid,
            equal_to(
                [
                    {
                        "icao24": "aabbcc",
                        "callsign": "SWA123",
                        "origin_country": "United States",
                        "time_position": 1710000000,
                        "last_contact": 1710000005,
                        "last_contact_at": datetime(
                            2024, 3, 9, 13, 0, 5, tzinfo=ZoneInfo("America/Sao_Paulo")
                        ),
                        "longitude": -46.6,
                        "latitude": -23.5,
                        "barometric_altitude_m": 1000.0,
                        "geometric_altitude_m": 1100.0,
                        "on_ground": False,
                        "velocity_mps": 120.0,
                        "velocity_kmh": 432.0,
                        "true_track_degrees": 180.0,
                        "vertical_rate_mps": 1.0,
                        "squawk": "1234",
                        "special_purpose_indicator": False,
                        "position_source": 0,
                        "aircraft_category": 1,
                        "source_time": 1710000000,
                        "ingested_at": "2026-09-14T10:00:00-03:00",
                        "execution_id": "exec-1",
                    }
                ]
            ),
        )

        normalized = normalize_state_vector(
            [
                "aabbcc",
                "SWA123 ",
                "United States",
                1710000000,
                1710000005,
                -46.6,
                -23.5,
                1000.0,
                False,
                120.0,
                180.0,
                1.0,
                5.0,
                None,
                1100.0,
                "1234",
                False,
                0,
                1,
            ],
            {"execution_id": "exec-1", "ingested_at": "2026-09-14T10:00:00-03:00"},
            1710000000,
        )
        assert normalized["last_contact_at"].tzinfo.key == "America/Sao_Paulo"
        assert normalized["last_contact_at"].utcoffset() == timedelta(hours=-3)


def test_missing_coordinates_are_rejected():
    record = {
        "_metadata": {"execution_id": "exec-2", "ingested_at": "2026-09-14T10:00:00Z"},
        "state": [
            "icao",
            "ABC123",
            None,
            1,
            2,
            None,
            None,
            None,
            False,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            0,
            None,
        ],
        "source_time": 1,
    }

    with BeamTestPipeline() as pipeline:
        rejected = (
            pipeline
            | beam.Create([record])
            | beam.ParDo(ValidateAndNormalizeAircraftState()).with_outputs(
                REJECTED_TAG, main="valid"
            )
        )
        assert_that(
            rejected.rejected,
            equal_to(
                [
                    {
                        "record": record,
                        "rejection_reason": "missing_coordinates",
                    }
                ]
            ),
        )


def test_last_contact_is_converted_to_sao_paulo_time():
    record = {
        "_metadata": {
            "source": "opensky_network",
            "execution_id": "exec-3",
            "collection_number": 1,
            "ingested_at": "2026-09-14T10:00:00-03:00",
            "bounding_box": {
                "lat_min": -24.2,
                "lon_min": -47.2,
                "lat_max": -22.7,
                "lon_max": -45.5,
            },
        },
        "payload": {
            "time": 1710000010,
            "states": [
                [
                    "aabbcc",
                    "SWA123 ",
                    "United States",
                    1710000000,
                    1710000005,
                    -46.6,
                    -23.5,
                    1000.0,
                    False,
                    120.0,
                    180.0,
                    1.0,
                    5.0,
                    None,
                    1100.0,
                    "1234",
                    False,
                    0,
                    1,
                ]
            ],
        },
    }

    with BeamTestPipeline() as pipeline:
        valid = (
            pipeline
            | beam.Create([json.dumps(record)])
            | beam.ParDo(ParseEnvelope()).with_outputs(REJECTED_TAG, main="valid")
        )
        assert_that(
            valid.valid,
            equal_to(
                [
                    {
                        "icao24": "aabbcc",
                        "callsign": "SWA123",
                        "origin_country": "United States",
                        "time_position": 1710000000,
                        "last_contact": 1710000005,
                        "last_contact_at": datetime(
                            2024, 3, 9, 13, 0, 5, tzinfo=ZoneInfo("America/Sao_Paulo")
                        ),
                        "longitude": -46.6,
                        "latitude": -23.5,
                        "barometric_altitude_m": 1000.0,
                        "geometric_altitude_m": 1100.0,
                        "on_ground": False,
                        "velocity_mps": 120.0,
                        "velocity_kmh": 432.0,
                        "true_track_degrees": 180.0,
                        "vertical_rate_mps": 1.0,
                        "squawk": "1234",
                        "special_purpose_indicator": False,
                        "position_source": 0,
                        "aircraft_category": 1,
                        "source_time": 1710000000,
                        "ingested_at": "2026-09-14T10:00:00-03:00",
                        "execution_id": "exec-3",
                    }
                ]
            ),
        )

        normalized = normalize_state_vector(
            [
                "aabbcc",
                "SWA123 ",
                "United States",
                1710000000,
                1710000005,
                -46.6,
                -23.5,
                1000.0,
                False,
                120.0,
                180.0,
                1.0,
                5.0,
                None,
                1100.0,
                "1234",
                False,
                0,
                1,
            ],
            {"execution_id": "exec-3", "ingested_at": "2026-09-14T10:00:00-03:00"},
            1710000000,
        )
        assert normalized["last_contact_at"].tzinfo.key == "America/Sao_Paulo"
        assert normalized["last_contact_at"].utcoffset() == timedelta(hours=-3)


def test_pipeline_writes_silver_and_rejected_outputs(tmp_path, monkeypatch):
    silver_output = tmp_path / "silver" / "aircraft_states"
    rejected_output = tmp_path / "rejected" / "aircraft_states"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bronze_to_silver",
            f"--input={FIXTURE}",
            f"--silver-output={silver_output}",
            f"--rejected-output={rejected_output}",
            "--runner=DirectRunner",
            "--direct_num_workers=1",
        ],
    )

    run()

    parquet_files = list(silver_output.parent.glob("aircraft_states-*.parquet"))
    rejected_files = list(rejected_output.parent.glob("rejected-*.jsonl"))
    assert len(parquet_files) == 1
    assert len(rejected_files) == 1

    silver_records = pq.read_table(parquet_files[0]).to_pylist()
    assert len(silver_records) >= 2
    assert all(record["callsign"].strip() for record in silver_records)

    rejected_records = [
        json.loads(line) for line in rejected_files[0].read_text().splitlines() if line
    ]
    assert len(rejected_records) >= 1
