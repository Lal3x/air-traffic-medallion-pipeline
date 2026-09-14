"""Coleta respostas OpenSky e grava envelopes JSONL na camada Bronze."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
from zoneinfo import ZoneInfo

from air_traffic_beam.collectors.opensky_client import OpenSkyClient
from air_traffic_beam.config.settings import Settings
from air_traffic_beam.exceptions import OpenSkyConfigurationError
from air_traffic_beam.observability.run_report import write_run_report

logger = logging.getLogger(__name__)
SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def _validate_bounds(args):
    """Valida a caixa geográfica antes de iniciar chamadas externas."""
    if args.lat_min >= args.lat_max:
        raise OpenSkyConfigurationError("lat_min deve ser menor que lat_max")
    if args.lon_min >= args.lon_max:
        raise OpenSkyConfigurationError("lon_min deve ser menor que lon_max")
    if not -90 <= args.lat_min <= 90 or not -90 <= args.lat_max <= 90:
        raise OpenSkyConfigurationError("latitude fora do intervalo válido [-90, 90]")
    if not -180 <= args.lon_min <= 180 or not -180 <= args.lon_max <= 180:
        raise OpenSkyConfigurationError(
            "longitude fora do intervalo válido [-180, 180]"
        )


def _build_envelope(
    response: dict, execution_id: str, collection_number: int, bounds: dict
) -> dict:
    """Envolve o payload bruto com metadados de ingestão e execução."""
    return {
        "_metadata": {
            "source": "opensky_network",
            "endpoint": "/states/all",
            "ingested_at": datetime.now(SAO_PAULO_TZ).isoformat(),
            "execution_id": execution_id,
            "collection_number": collection_number,
            "schema_version": 1,
            "bounding_box": bounds,
        },
        "payload": response,
    }


def collect_once(settings: Settings, args) -> dict:
    """Executa uma coleta única, útil para integração e testes."""
    client = OpenSkyClient(settings)
    response = client.get_states()
    execution_id = str(uuid4())
    envelope = _build_envelope(response, execution_id, 1, settings.bounding_box)
    return envelope


def write_jsonl_atomic(path: Path, payload: dict | list[dict]) -> None:
    """Escreve JSONL atomicamente para evitar arquivo parcial na Bronze."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    records = payload if isinstance(payload, list) else [payload]
    try:
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent), suffix=".tmp", delete=False
        ) as temp_file:
            temporary_path = Path(temp_file.name)
            for record in records:
                temp_file.write(json.dumps(record, ensure_ascii=False))
                temp_file.write("\n")
            temp_file.flush()
        temporary_path.replace(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def parse_arguments() -> argparse.Namespace:
    """Define limites, intervalo, número de coletas e destino Bronze."""
    parser = argparse.ArgumentParser(
        description="Coleta estados de aeronaves da OpenSky Network."
    )
    parser.add_argument("--lat-min", type=float, default=-24.2)
    parser.add_argument("--lon-min", type=float, default=-47.2)
    parser.add_argument("--lat-max", type=float, default=-22.7)
    parser.add_argument("--lon-max", type=float, default=-45.5)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--max-collections", type=int, default=5)
    parser.add_argument("--output", default="data/bronze/aircraft_states")
    return parser.parse_args()


def run() -> str:
    """Executa coletas finitas e grava o relatório de observabilidade.

    Returns:
        Caminho do relatório JSON da coleta atual.
    """
    args = parse_arguments()
    _validate_bounds(args)
    settings = Settings(
        opensky_api_base_url=os.getenv(
            "OPENSKY_API_BASE_URL", "https://opensky-network.org/api"
        ),
        opensky_lat_min=args.lat_min,
        opensky_lon_min=args.lon_min,
        opensky_lat_max=args.lat_max,
        opensky_lon_max=args.lon_max,
        opensky_request_timeout_seconds=int(
            os.getenv("OPENSKY_REQUEST_TIMEOUT_SECONDS", "30")
        ),
        opensky_interval_seconds=args.interval_seconds,
        opensky_max_collections=args.max_collections,
        bronze_base_path=Path(args.output),
    )
    execution_id = str(uuid4())
    batch_started_at = datetime.now(SAO_PAULO_TZ)
    batch_envelopes: list[dict] = []
    started = time.perf_counter()
    output_paths: list[str] = []
    total_records = 0
    try:
        for collection_number in range(1, args.max_collections + 1):
            response = OpenSkyClient(settings).get_states()
            envelope = _build_envelope(
                response, execution_id, collection_number, settings.bounding_box
            )
            batch_envelopes.append(envelope)
            total_records += len(response.get("states", []))
            logger.info(
                "Received %s aircraft states on collection %s",
                len(response.get("states", [])),
                collection_number,
            )
            if collection_number == args.max_collections:
                break
            if args.interval_seconds > 0:
                time.sleep(args.interval_seconds)
        output_dir = (
            Path(args.output)
            / f"ingestion_date={batch_started_at.strftime('%Y-%m-%d')}"
            / f"hour={batch_started_at.strftime('%H')}"
        )
        output_file = output_dir / f"microbatch_{execution_id}.jsonl"
        write_jsonl_atomic(output_file, batch_envelopes)
        output_paths.append(str(output_file))
    except Exception as exc:
        if batch_envelopes:
            output_dir = (
                Path(args.output)
                / f"ingestion_date={batch_started_at.strftime('%Y-%m-%d')}"
                / f"hour={batch_started_at.strftime('%H')}"
            )
            output_file = output_dir / f"microbatch_{execution_id}_partial.jsonl"
            write_jsonl_atomic(output_file, batch_envelopes)
            output_paths.append(str(output_file))
        write_run_report(
            "collector",
            settings.observability_base_path,
            status="failed",
            duration_seconds=time.perf_counter() - started,
            output_records=total_records,
            output_paths=output_paths,
            error_message=str(exc),
        )
        raise
    return write_run_report(
        "collector",
        settings.observability_base_path,
        duration_seconds=time.perf_counter() - started,
        input_records=total_records,
        output_records=total_records,
        output_paths=output_paths,
    )


if __name__ == "__main__":
    run()
