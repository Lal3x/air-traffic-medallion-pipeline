"""Orquestra coleta, Bronze → Silver e Silver → Gold no DirectRunner local."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from air_traffic_beam.collectors.aircraft_states import run as collect_run
from air_traffic_beam.logging_config import configure_logging
from air_traffic_beam.pipelines.bronze_to_silver import run as bronze_to_silver_run
from air_traffic_beam.pipelines.silver_to_gold import run as silver_to_gold_run

LOG_PATH = Path("data/observability/logs/pipeline.log")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Lê parâmetros da execução completa, incluindo o modo verbose."""
    parser = argparse.ArgumentParser(
        description="Executa a coleta, Bronze→Silver e Silver→Gold em sequência."
    )
    parser.add_argument("--lat-min", type=float, default=-24.2)
    parser.add_argument("--lon-min", type=float, default=-47.2)
    parser.add_argument("--lat-max", type=float, default=-22.7)
    parser.add_argument("--lon-max", type=float, default=-45.5)
    parser.add_argument("--interval-seconds", type=int, default=1)
    parser.add_argument("--max-collections", type=int, default=1)
    parser.add_argument("--output", default="data/bronze/aircraft_states")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe INFO técnico do Apache Beam e Prism no terminal.",
    )
    return parser.parse_args()


def _read_report(report_path: str) -> dict:
    """Carrega o relatório produzido pela etapa recém-finalizada."""
    return json.loads(Path(report_path).read_text(encoding="utf-8"))


def _format_duration(seconds: float) -> str:
    """Formata uma duração em segundos com convenção decimal portuguesa."""
    return f"{seconds:.1f}".replace(".", ",")


def _print_stage_summary(label: str, report: dict) -> None:
    """Apresenta no terminal métricas reais de uma etapa do pipeline."""
    output_paths = report.get("output_paths") or []
    primary_path = output_paths[0] if output_paths else "nenhum"
    print(f"{label}: {report.get('status', 'unknown')}")
    print(
        f"  Duração: {_format_duration(report.get('duration_seconds', 0.0))} segundos"
    )
    print(f"  Registros lidos: {report.get('input_records', 0)}")
    print(f"  Registros gravados: {report.get('output_records', 0)}")
    print(f"  Registros rejeitados: {report.get('rejected_records', 0)}")
    print(f"  Caminho principal: {primary_path}")


def main() -> int:
    """Executa as três camadas em sequência e retorna o código do processo."""
    args = parse_args()
    log_path = configure_logging(verbose=args.verbose, log_path=LOG_PATH)
    started = time.perf_counter()
    failed_stage = "inicialização"
    try:
        print("[1/3] Coletando dados da OpenSky")
        failed_stage = "coleta"
        sys.argv = [
            "aircraft_states",
            f"--lat-min={args.lat_min}",
            f"--lon-min={args.lon_min}",
            f"--lat-max={args.lat_max}",
            f"--lon-max={args.lon_max}",
            f"--interval-seconds={args.interval_seconds}",
            f"--max-collections={args.max_collections}",
            f"--output={args.output}",
        ]
        collector_report = _read_report(collect_run())
        _print_stage_summary("Coleta", collector_report)

        print("[2/3] Processando Bronze → Silver")
        failed_stage = "Bronze → Silver"
        collector_paths = [
            Path(path) for path in collector_report.get("output_paths", [])
        ]
        if not collector_paths:
            raise RuntimeError("A coleta não produziu arquivo Bronze")
        input_pattern = str(collector_paths[0])
        sys.argv = [
            "bronze_to_silver",
            f"--input={input_pattern}",
            "--silver-output=data/silver/aircraft_states/aircraft_states",
            "--rejected-output=data/rejected/aircraft_states/rejected",
            "--runner=DirectRunner",
            "--direct_num_workers=1",
        ]
        silver_report = _read_report(bronze_to_silver_run())
        _print_stage_summary("Bronze → Silver", silver_report)

        print("[3/3] Processando Silver → Gold")
        failed_stage = "Silver → Gold"
        sys.argv = [
            "silver_to_gold",
            f"--input={silver_report.get('output_paths', ['data/silver/aircraft_states'])[0]}",
            "--latest-output=data/gold/latest/latest_aircraft_states",
            "--summary-output=data/gold/traffic/traffic_summary",
            "--runner=DirectRunner",
            "--direct_num_workers=1",
        ]
        gold_report = _read_report(silver_to_gold_run())
        _print_stage_summary("Silver → Gold", gold_report)

        print("Pipeline concluído")
        print(f"Duração: {_format_duration(time.perf_counter() - started)} segundos")
        print(f"Coletados: {collector_report.get('output_records', 0)}")
        print(f"Silver válidos: {silver_report.get('output_records', 0)}")
        print(f"Rejeitados: {silver_report.get('rejected_records', 0)}")
        print(
            f"Gold atualizado: {'sim' if gold_report.get('output_records', 0) > 0 else 'não'}"
        )
        print(f"Log técnico: {log_path}")
        return 0
    except Exception as exc:
        logger.exception("Falha na etapa %s", failed_stage)
        print(f"Falha na etapa: {failed_stage}")
        print(f"Detalhe: {exc}")
        print(f"Log técnico: {log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
