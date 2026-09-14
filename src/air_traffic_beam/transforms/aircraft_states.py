"""Regras de parsing, validação e normalização dos state vectors OpenSky."""

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import apache_beam as beam
from apache_beam.pvalue import TaggedOutput

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

REJECTED_TAG = "rejected"

STATE_INDEXES = {
    "icao24": 0,
    "callsign": 1,
    "origin_country": 2,
    "time_position": 3,
    "last_contact": 4,
    "longitude": 5,
    "latitude": 6,
    "baro_altitude": 7,
    "on_ground": 8,
    "velocity": 9,
    "true_track": 10,
    "vertical_rate": 11,
    "sensors": 12,
    "geo_altitude": 13,
    "squawk": 14,
    "spi": 15,
    "position_source": 16,
    "category": 17,
}


def _to_local_datetime(value: Any) -> datetime | None:
    """Converte epoch Unix para horário local de São Paulo."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), SAO_PAULO_TZ)
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_state_vector(
    state: list[Any], metadata: dict[str, Any] | None, source_time: Any
) -> dict[str, Any]:
    """Converte a lista posicional OpenSky em um registro Silver.

    A API retorna os campos no contrato posicional descrito por
    ``STATE_INDEXES``. A função valida identificador e coordenadas, converte
    velocidade de m/s para km/h e cria o timestamp em fuso de São Paulo.

    Raises:
        ValueError: quando o vetor é curto, não identifica a aeronave ou possui
            coordenadas ausentes/fora do intervalo.
    """
    if not isinstance(state, list) or len(state) < 17:
        raise ValueError("state_vector_too_short")

    icao24 = state[STATE_INDEXES["icao24"]]
    if icao24 is None or str(icao24).strip() == "":
        raise ValueError("missing_aircraft_identifier")

    callsign = state[STATE_INDEXES["callsign"]]
    callsign_value = None if callsign is None else str(callsign).strip() or None

    longitude = state[STATE_INDEXES["longitude"]]
    latitude = state[STATE_INDEXES["latitude"]]
    if longitude is None or latitude is None:
        raise ValueError("missing_coordinates")

    try:
        longitude_value = float(longitude)
        latitude_value = float(latitude)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive path
        raise ValueError("invalid_coordinates_type") from exc

    if not -90.0 <= latitude_value <= 90.0:
        raise ValueError("latitude_out_of_range")
    if not -180.0 <= longitude_value <= 180.0:
        raise ValueError("longitude_out_of_range")

    # O índice 9 da resposta OpenSky é velocidade em m/s; a Silver também expõe km/h.
    velocity_value = state[STATE_INDEXES["velocity"]]
    velocity_mps = None if velocity_value is None else float(velocity_value)
    velocity_kmh = None if velocity_mps is None else velocity_mps * 3.6

    # Os índices são parte do contrato posicional da API, não nomes JSON.
    measurement_time = state[STATE_INDEXES["time_position"]]
    canonical_source_time = (
        measurement_time if measurement_time is not None else source_time
    )
    if source_time is None:
        source_time = canonical_source_time

    geo_altitude = state[STATE_INDEXES["geo_altitude"]]
    squawk = state[STATE_INDEXES["squawk"]]
    special_purpose_indicator = state[STATE_INDEXES["spi"]]
    position_source = state[STATE_INDEXES["position_source"]]
    aircraft_category = (
        state[STATE_INDEXES["category"]]
        if len(state) > STATE_INDEXES["category"]
        else None
    )

    if (
        len(state) > 18
        and state[STATE_INDEXES["geo_altitude"]] is None
        and state[STATE_INDEXES["geo_altitude"] + 1] is not None
    ):
        geo_altitude = state[STATE_INDEXES["geo_altitude"] + 1]
        squawk = state[STATE_INDEXES["geo_altitude"] + 2]
        special_purpose_indicator = state[STATE_INDEXES["geo_altitude"] + 3]
        position_source = state[STATE_INDEXES["geo_altitude"] + 4]
        aircraft_category = state[STATE_INDEXES["geo_altitude"] + 5]

    return {
        "icao24": str(icao24),
        "callsign": callsign_value,
        "origin_country": state[STATE_INDEXES["origin_country"]],
        "time_position": measurement_time,
        "last_contact": state[STATE_INDEXES["last_contact"]],
        "last_contact_at": _to_local_datetime(state[STATE_INDEXES["last_contact"]]),
        "longitude": longitude_value,
        "latitude": latitude_value,
        "barometric_altitude_m": state[STATE_INDEXES["baro_altitude"]],
        "geometric_altitude_m": geo_altitude,
        "on_ground": bool(state[STATE_INDEXES["on_ground"]]),
        "velocity_mps": velocity_mps,
        "velocity_kmh": velocity_kmh,
        "true_track_degrees": state[STATE_INDEXES["true_track"]],
        "vertical_rate_mps": state[STATE_INDEXES["vertical_rate"]],
        "squawk": squawk,
        "special_purpose_indicator": special_purpose_indicator,
        "position_source": position_source,
        "aircraft_category": aircraft_category,
        "source_time": canonical_source_time,
        "ingested_at": metadata.get("ingested_at")
        if isinstance(metadata, dict)
        else None,
        "execution_id": metadata.get("execution_id")
        if isinstance(metadata, dict)
        else None,
    }


class ParseEnvelope(beam.DoFn):
    """Expande um envelope Bronze em aeronaves ou rejeições tagged output."""

    def process(self, line: str):
        """Lê uma linha JSON e envia válidos ao fluxo principal ou rejeitados."""
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            yield TaggedOutput(
                REJECTED_TAG,
                {
                    "raw_record": line,
                    "rejection_reason": "invalid_json",
                    "error_message": str(exc),
                },
            )
            return

        if not isinstance(record, dict):
            yield TaggedOutput(
                REJECTED_TAG, {"record": record, "rejection_reason": "invalid_envelope"}
            )
            return

        metadata = record.get("_metadata")
        payload = record.get("payload")

        if isinstance(metadata, dict) and isinstance(payload, dict):
            states = payload.get("states")
            source_time = payload.get("time")
            metadata_payload = metadata
        elif "states" in record:
            states = record.get("states")
            source_time = record.get("time")
            metadata_payload = metadata if isinstance(metadata, dict) else {}
        else:
            yield TaggedOutput(
                REJECTED_TAG, {"record": record, "rejection_reason": "invalid_envelope"}
            )
            return

        if states is None:
            return
        if not isinstance(states, list):
            yield TaggedOutput(
                REJECTED_TAG, {"record": record, "rejection_reason": "invalid_states"}
            )
            return

        for state in states:
            if not isinstance(state, list):
                yield TaggedOutput(
                    REJECTED_TAG,
                    {"record": record, "rejection_reason": "invalid_state_vector"},
                )
                continue
            if len(state) < 17:
                yield TaggedOutput(
                    REJECTED_TAG,
                    {"record": record, "rejection_reason": "state_vector_too_short"},
                )
                continue
            try:
                yield normalize_state_vector(state, metadata_payload, source_time)
            except ValueError as exc:
                yield TaggedOutput(
                    REJECTED_TAG, {"record": record, "rejection_reason": str(exc)}
                )


class ValidateAndNormalizeAircraftState(beam.DoFn):
    """Valida registros individuais antes da gravação da camada Silver."""

    def process(self, record: dict[str, Any]):
        """Emite o registro normalizado ou uma rejeição com o motivo."""
        if "icao24" in record and "latitude" in record and "longitude" in record:
            normalized = dict(record)
        else:
            metadata = record.get("_metadata") if isinstance(record, dict) else None
            state = record.get("state") if isinstance(record, dict) else None
            if not isinstance(metadata, dict) or not isinstance(state, list):
                yield TaggedOutput(
                    REJECTED_TAG,
                    {"record": record, "rejection_reason": "invalid_state_vector"},
                )
                return
            try:
                normalized = normalize_state_vector(
                    state, metadata, record.get("source_time")
                )
            except ValueError as exc:
                yield TaggedOutput(
                    REJECTED_TAG, {"record": record, "rejection_reason": str(exc)}
                )
                return

        longitude = normalized.get("longitude")
        latitude = normalized.get("latitude")
        if longitude is None or latitude is None:
            yield TaggedOutput(
                REJECTED_TAG,
                {"record": record, "rejection_reason": "missing_coordinates"},
            )
            return

        try:
            longitude_value = float(longitude)
            latitude_value = float(latitude)
        except (TypeError, ValueError):
            yield TaggedOutput(
                REJECTED_TAG,
                {"record": record, "rejection_reason": "invalid_coordinates_type"},
            )
            return

        if not -90.0 <= latitude_value <= 90.0:
            yield TaggedOutput(
                REJECTED_TAG,
                {"record": record, "rejection_reason": "latitude_out_of_range"},
            )
            return
        if not -180.0 <= longitude_value <= 180.0:
            yield TaggedOutput(
                REJECTED_TAG,
                {"record": record, "rejection_reason": "longitude_out_of_range"},
            )
            return

        yield normalized
