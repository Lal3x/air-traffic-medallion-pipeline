"""Schema Arrow da camada Silver normalizada."""

import pyarrow as pa

SILVER_AIRCRAFT_SCHEMA = pa.schema(
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
