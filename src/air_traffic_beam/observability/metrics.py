"""Modelo serializável dos relatórios de execução do pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


@dataclass
class PipelineRunReport:
    """Representa contagens, duração, status e artefatos de uma etapa."""

    run_id: str = field(default_factory=lambda: str(uuid4()))
    pipeline: str = "unknown"
    status: str = "success"
    started_at: str = field(
        default_factory=lambda: datetime.now(SAO_PAULO_TZ).isoformat()
    )
    finished_at: str | None = None
    duration_seconds: float = 0.0
    input_files: int = 0
    input_records: int = 0
    output_records: int = 0
    rejected_records: int = 0
    missing_position_records: int = 0
    error_rate: float = 0.0
    output_paths: list[str] = field(default_factory=list)
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Converte o relatório para o formato persistido em JSON."""
        return {
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "input_files": self.input_files,
            "input_records": self.input_records,
            "output_records": self.output_records,
            "rejected_records": self.rejected_records,
            "missing_position_records": self.missing_position_records,
            "error_rate": self.error_rate,
            "output_paths": self.output_paths,
            "error_message": self.error_message,
        }

    def write(self, base_dir: str | Path) -> Path:
        """Cria o diretório de observabilidade e grava o relatório JSON."""
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        report_path = path / f"{self.pipeline}-{self.run_id}.json"
        report_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report_path
