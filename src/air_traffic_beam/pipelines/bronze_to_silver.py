"""Transforma envelopes JSONL da Bronze em registros Silver tipados.

Este módulo representa a principal etapa de qualidade da arquitetura medalhão:
os dados brutos são lidos como uma PCollection, expandidos em state vectors,
validados e separados em registros válidos e rejeitados. O DirectRunner
processa a PCollection de forma distribuída dentro do pipeline; o código não
monta uma lista Python com todos os envelopes antes de iniciar o Beam.
"""

import argparse
import json
import logging
import time
from pathlib import Path
from uuid import uuid4

import apache_beam as beam
from apache_beam.io.parquetio import WriteToParquet
from apache_beam.options.pipeline_options import PipelineOptions

from air_traffic_beam.observability.artifacts import (
    count_jsonl_records,
    count_parquet_records,
    expand_paths,
)
from air_traffic_beam.observability.run_report import write_run_report
from air_traffic_beam.schemas.silver import SILVER_AIRCRAFT_SCHEMA
from air_traffic_beam.transforms.aircraft_states import (
    REJECTED_TAG,
    ParseEnvelope,
    ValidateAndNormalizeAircraftState,
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Define os caminhos de entrada e saída da etapa Bronze → Silver."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/bronze/aircraft_states/**/*.jsonl")
    parser.add_argument(
        "--silver-output", default="data/silver/aircraft_states/aircraft_states"
    )
    parser.add_argument(
        "--rejected-output", default="data/rejected/aircraft_states/rejected"
    )
    return parser.parse_known_args()


def run() -> str:
    """Executa a transformação Bronze → Silver e grava um relatório.

    Returns:
        Caminho do relatório JSON da execução atual.

    Raises:
        OSError: se os sinks não puderem ser criados.
        ValueError: se uma configuração de entrada for inválida.
    """
    arguments, beam_arguments = parse_arguments()
    run_id = str(uuid4())
    silver_prefix = f"{arguments.silver_output}-{run_id}"
    Path(silver_prefix).parent.mkdir(parents=True, exist_ok=True)

    rejected_prefix = arguments.rejected_output
    rejected_path = Path(arguments.rejected_output)
    if rejected_path.name == "aircraft_states":
        rejected_prefix = str(rejected_path.parent / "rejected")
    rejected_prefix = f"{rejected_prefix}-{run_id}"
    Path(rejected_prefix).parent.mkdir(parents=True, exist_ok=True)

    options = PipelineOptions(beam_arguments)
    started = time.perf_counter()

    with beam.Pipeline(options=options) as pipeline:
        lines = pipeline | "Ler arquivos Bronze" >> beam.io.ReadFromText(
            arguments.input
        )
        parsed = lines | "Validar envelopes" >> beam.ParDo(
            ParseEnvelope()
        ).with_outputs(REJECTED_TAG, main="valid")
        normalized = parsed.valid | "Normalizar aeronaves" >> beam.ParDo(
            ValidateAndNormalizeAircraftState()
        ).with_outputs(REJECTED_TAG, main="valid")
        rejected = (
            (parsed.rejected, normalized.rejected)
            | "Combinar rejeitados" >> beam.Flatten()
            | "Serializar rejeitados"
            >> beam.Map(
                lambda record: json.dumps(record, ensure_ascii=False, default=str)
            )
        )

        normalized.valid | "Gravar Silver Parquet" >> WriteToParquet(
            file_path_prefix=silver_prefix,
            schema=SILVER_AIRCRAFT_SCHEMA,
            file_name_suffix=".parquet",
            num_shards=1,
        )

        rejected | "Gravar rejeitados JSONL" >> beam.io.WriteToText(
            file_path_prefix=rejected_prefix,
            file_name_suffix=".jsonl",
            num_shards=1,
        )

    input_files = expand_paths(arguments.input)
    silver_files = expand_paths(f"{silver_prefix}-*.parquet")
    rejected_files = expand_paths(f"{rejected_prefix}-*.jsonl")
    # Contamos apenas os prefixes UUID desta execução para não misturar histórico.
    input_records = count_jsonl_records(input_files)
    rejected_records = count_jsonl_records(rejected_files)
    output_records = count_parquet_records(silver_files)
    if output_records == 0:
        logger.warning("Nenhum registro Silver válido foi produzido nesta execução")
    if rejected_records == 0:
        logger.info("Nenhum registro rejeitado foi produzido nesta execução")
    return write_run_report(
        "bronze_to_silver",
        "data/observability",
        input_files=len(input_files),
        input_records=input_records,
        output_records=output_records,
        rejected_records=rejected_records,
        duration_seconds=time.perf_counter() - started,
        error_rate=rejected_records / input_records if input_records else 0.0,
        output_paths=[str(path) for path in silver_files],
    )


if __name__ == "__main__":
    run()
