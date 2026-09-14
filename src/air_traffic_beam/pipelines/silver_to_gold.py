"""Agrega a Silver em visões Gold para consumo analítico e no dashboard.

A etapa lê arquivos Parquet por nome, cria uma PCollection de registros e
produz duas saídas: a última posição por aeronave e um resumo do tráfego.
Cada execução usa um prefixo UUID, preservando histórico sem sobrescrever
artefatos anteriores.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import apache_beam as beam
from apache_beam.io.parquetio import ReadAllFromParquet
from apache_beam.options.pipeline_options import PipelineOptions

from air_traffic_beam.observability.artifacts import count_parquet_records, expand_paths
from air_traffic_beam.observability.run_report import write_run_report

logger = logging.getLogger(__name__)


def parse_arguments():
    """Define a entrada Silver e os dois destinos Gold."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/silver/aircraft_states")
    parser.add_argument(
        "--latest-output", default="data/gold/latest/latest_aircraft_states"
    )
    parser.add_argument("--summary-output", default="data/gold/traffic/traffic_summary")
    return parser.parse_known_args()


def _contact_key(record: dict[str, Any]) -> int:
    """Retorna o contato Unix usado para ordenar observações da aeronave."""
    value = record.get("last_contact")
    return int(value) if value is not None else -1


def _latest_by_aircraft(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Escolhe a observação mais recente de um mesmo `icao24`."""
    latest = records[0]
    for record in records[1:]:
        if _contact_key(record) > _contact_key(latest):
            latest = record
    return latest


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula indicadores agregados de uma coleção de observações Silver."""
    velocities = [
        record["velocity_kmh"]
        for record in records
        if record.get("velocity_kmh") is not None
    ]
    altitudes = [
        record["geometric_altitude_m"]
        for record in records
        if record.get("geometric_altitude_m") is not None
    ]
    return {
        "aircraft_observations": len(records),
        "unique_aircraft": len({record["icao24"] for record in records}),
        "airborne_aircraft": sum(
            not record.get("on_ground", False) for record in records
        ),
        "on_ground_aircraft": sum(record.get("on_ground", False) for record in records),
        "average_velocity_kmh": sum(velocities) / len(velocities)
        if velocities
        else None,
        "average_geometric_altitude_m": sum(altitudes) / len(altitudes)
        if altitudes
        else None,
        "latest_contact": max(
            (_contact_key(record) for record in records), default=None
        ),
    }


def run() -> str:
    """Executa a agregação Silver → Gold e grava o relatório da execução.

    Returns:
        Caminho do relatório JSON produzido.

    Raises:
        FileNotFoundError: quando não há Parquet Silver para processar.
    """
    arguments, beam_arguments = parse_arguments()
    run_id = str(uuid4())
    latest_prefix = f"{arguments.latest_output}-{run_id}"
    summary_prefix = f"{arguments.summary_output}-{run_id}"
    Path(latest_prefix).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_prefix).parent.mkdir(parents=True, exist_ok=True)
    options = PipelineOptions(beam_arguments)
    started = time.perf_counter()

    input_path = Path(arguments.input)
    if input_path.is_dir():
        parquet_files = sorted(str(path) for path in input_path.rglob("*.parquet"))
    elif input_path.is_file():
        parquet_files = [str(input_path)]
    else:
        parquet_files = sorted(
            str(path) for path in input_path.parent.glob(input_path.name)
        )
    if not parquet_files:
        raise FileNotFoundError(f"No Silver Parquet files found at {arguments.input}")

    with beam.Pipeline(options=options) as pipeline:
        records = (
            pipeline
            | "Listar arquivos Silver" >> beam.Create(parquet_files)
            | "Ler Silver Parquet" >> ReadAllFromParquet()
        )
        latest = (
            records
            | "Agrupar por aeronave"
            >> beam.Map(lambda record: (record["icao24"], record))
            | "Combinar observações por aeronave" >> beam.GroupByKey()
            | "Selecionar posição mais recente"
            >> beam.Map(lambda item: _latest_by_aircraft(list(item[1])))
        )
        (
            latest
            | "Serializar Gold atual"
            >> beam.Map(json.dumps, ensure_ascii=False, default=str)
            | "Gravar Gold atual"
            >> beam.io.WriteToText(
                file_path_prefix=latest_prefix,
                file_name_suffix=".jsonl",
                num_shards=1,
            )
        )

        summary = (
            records
            | "Coletar observações do resumo" >> beam.combiners.ToList()
            | "Construir resumo Gold" >> beam.Map(_summary)
        )
        (
            summary
            | "Serializar resumo Gold"
            >> beam.Map(json.dumps, ensure_ascii=False, default=str)
            | "Gravar resumo Gold"
            >> beam.io.WriteToText(
                file_path_prefix=summary_prefix,
                file_name_suffix=".jsonl",
                num_shards=1,
            )
        )

    latest_files = expand_paths(f"{latest_prefix}-*.jsonl")
    summary_files = expand_paths(f"{summary_prefix}-*.jsonl")
    latest_records = sum(
        1
        for path in latest_files
        if path.exists()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    )
    if latest_records == 0:
        logger.warning("Nenhum registro Gold válido foi produzido nesta execução")
    if not summary_files:
        logger.warning("Nenhum resumo Gold foi produzido nesta execução")
    return write_run_report(
        "silver_to_gold",
        "data/observability",
        input_files=len(parquet_files),
        input_records=count_parquet_records([Path(path) for path in parquet_files]),
        output_records=latest_records,
        duration_seconds=time.perf_counter() - started,
        output_paths=[str(path) for path in latest_files + summary_files],
    )


if __name__ == "__main__":
    run()
