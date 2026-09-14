"""Leitura e contagem de artefatos locais usados nas métricas das etapas."""

from __future__ import annotations

import json
from glob import glob
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


def expand_paths(pattern: str, suffix: str | None = None) -> list[Path]:
    """Expande diretório, arquivo ou glob recursivo em caminhos concretos."""
    if "*" in pattern:
        return sorted(Path(path) for path in glob(pattern, recursive=True))
    path = Path(pattern)
    if path.is_dir():
        return sorted(path.rglob(suffix or "*"))
    if path.is_file():
        return [path]
    return sorted(path.parent.glob(path.name))


def count_jsonl_records(paths: list[Path]) -> int:
    """Conta linhas não vazias de arquivos JSONL existentes."""
    return sum(
        1
        for path in paths
        if path.exists()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    )


def count_parquet_records(paths: list[Path]) -> int:
    """Conta linhas Parquet via metadata sem carregar tabelas na memória."""
    return sum(pq.read_metadata(path).num_rows for path in paths if path.exists())


def read_jsonl_records(paths: list[Path]) -> list[dict[str, Any]]:
    """Lê JSONL em dicionários para inspeção local e testes."""
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records
