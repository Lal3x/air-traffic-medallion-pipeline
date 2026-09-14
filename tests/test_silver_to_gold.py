import json
import sys

import pyarrow as pa
import pyarrow.parquet as pq

from air_traffic_beam.pipelines.silver_to_gold import run

SILVER_SCHEMA = pa.schema(
    [
        ("icao24", pa.string()),
        ("callsign", pa.string()),
        ("origin_country", pa.string()),
        ("time_position", pa.int64()),
        ("last_contact", pa.int64()),
        ("last_contact_at", pa.timestamp("us", tz="America/Sao_Paulo")),
        ("longitude", pa.float64()),
        ("latitude", pa.float64()),
        ("barometric_altitude_m", pa.float64()),
        ("geometric_altitude_m", pa.float64()),
        ("on_ground", pa.bool_()),
        ("velocity_mps", pa.float64()),
        ("velocity_kmh", pa.float64()),
        ("true_track_degrees", pa.float64()),
        ("vertical_rate_mps", pa.float64()),
        ("squawk", pa.string()),
        ("special_purpose_indicator", pa.bool_()),
        ("position_source", pa.int64()),
        ("aircraft_category", pa.int64()),
        ("source_time", pa.int64()),
        ("ingested_at", pa.string()),
        ("execution_id", pa.string()),
    ]
)


def test_gold_writes_latest_aircraft_and_summary(tmp_path, monkeypatch):
    silver_dir = tmp_path / "silver"
    silver_dir.mkdir()
    rows = [
        {
            "icao24": "abc123",
            "callsign": "OLD",
            "origin_country": "Brazil",
            "time_position": 100,
            "last_contact": 100,
            "longitude": -46.6,
            "latitude": -23.5,
            "barometric_altitude_m": 900.0,
            "geometric_altitude_m": 950.0,
            "on_ground": False,
            "velocity_mps": 100.0,
            "velocity_kmh": 360.0,
            "true_track_degrees": 180.0,
            "vertical_rate_mps": 0.0,
            "squawk": None,
            "special_purpose_indicator": False,
            "position_source": 0,
            "aircraft_category": None,
            "source_time": 100,
            "ingested_at": "2026-09-14T00:00:00Z",
            "execution_id": "one",
        },
        {
            "icao24": "abc123",
            "callsign": "NEW",
            "origin_country": "Brazil",
            "time_position": 200,
            "last_contact": 200,
            "longitude": -46.7,
            "latitude": -23.4,
            "barometric_altitude_m": 1000.0,
            "geometric_altitude_m": 1050.0,
            "on_ground": False,
            "velocity_mps": 120.0,
            "velocity_kmh": 432.0,
            "true_track_degrees": 180.0,
            "vertical_rate_mps": 0.0,
            "squawk": None,
            "special_purpose_indicator": False,
            "position_source": 0,
            "aircraft_category": None,
            "source_time": 200,
            "ingested_at": "2026-09-14T00:01:00Z",
            "execution_id": "two",
        },
        {
            "icao24": "def456",
            "callsign": "GROUND",
            "origin_country": "Brazil",
            "time_position": 201,
            "last_contact": 201,
            "longitude": -46.8,
            "latitude": -23.6,
            "barometric_altitude_m": 0.0,
            "geometric_altitude_m": 0.0,
            "on_ground": True,
            "velocity_mps": 0.0,
            "velocity_kmh": 0.0,
            "true_track_degrees": 0.0,
            "vertical_rate_mps": 0.0,
            "squawk": None,
            "special_purpose_indicator": False,
            "position_source": 0,
            "aircraft_category": None,
            "source_time": 201,
            "ingested_at": "2026-09-14T00:01:00Z",
            "execution_id": "two",
        },
    ]
    pq.write_table(
        pa.Table.from_pylist(rows, schema=SILVER_SCHEMA),
        silver_dir / "aircraft_states-00000-of-00001.parquet",
    )

    latest_output = tmp_path / "gold" / "latest"
    summary_output = tmp_path / "gold" / "summary"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "silver_to_gold",
            f"--input={silver_dir}",
            f"--latest-output={latest_output}",
            f"--summary-output={summary_output}",
            "--runner=DirectRunner",
            "--direct_num_workers=1",
        ],
    )

    run()

    latest_file = min(latest_output.parent.glob("latest-*.jsonl"))
    summary_file = min(summary_output.parent.glob("summary-*.jsonl"))
    latest = [json.loads(line) for line in latest_file.read_text().splitlines() if line]
    summary = json.loads(summary_file.read_text().strip())
    selected = {record["icao24"]: record for record in latest}

    assert selected["abc123"]["callsign"] == "NEW"
    assert len(selected) == 2
    assert summary["aircraft_observations"] == 3
    assert summary["unique_aircraft"] == 2
    assert summary["airborne_aircraft"] == 2
    assert summary["on_ground_aircraft"] == 1
    assert summary["latest_contact"] == 201
