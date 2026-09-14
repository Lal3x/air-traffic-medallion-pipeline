"""Funções de criação e persistência dos relatórios de observabilidade."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from air_traffic_beam.config.settings import Settings
from air_traffic_beam.observability.metrics import PipelineRunReport

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def build_run_report(
    pipeline_name: str, status: str = "success", **kwargs
) -> PipelineRunReport:
    """Monta um relatório tipado a partir das métricas de uma etapa."""
    report = PipelineRunReport(pipeline=pipeline_name, status=status)
    for key, value in kwargs.items():
        if hasattr(report, key):
            setattr(report, key, value)
    return report


def write_run_report(pipeline_name: str, base_dir: str | Path, **kwargs) -> str:
    """Finaliza e grava um relatório, retornando seu caminho."""
    report = build_run_report(pipeline_name, **kwargs)
    report.finished_at = datetime.now(SAO_PAULO_TZ).isoformat()
    path = report.write(base_dir)
    return str(path)


def get_observability_dir() -> Path:
    """Retorna o diretório configurado para artefatos de observabilidade."""
    settings = Settings()
    return Path(settings.observability_base_path)
