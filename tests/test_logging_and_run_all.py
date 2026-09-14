import json
import logging
from argparse import Namespace
from pathlib import Path

import air_traffic_beam.run_all as run_all_module
from air_traffic_beam.logging_config import configure_logging


def _write_report(
    path: Path,
    pipeline: str,
    output_path: str,
    output_records: int,
    rejected_records: int = 0,
) -> None:
    path.write_text(
        json.dumps(
            {
                "pipeline": pipeline,
                "status": "success",
                "duration_seconds": 0.1,
                "input_records": output_records,
                "output_records": output_records,
                "rejected_records": rejected_records,
                "output_paths": [output_path],
            }
        ),
        encoding="utf-8",
    )


def test_logging_separates_terminal_summary_from_technical_file(tmp_path, capsys):
    log_path = tmp_path / "pipeline.log"
    configure_logging(log_path=log_path)
    logging.getLogger("air_traffic_beam.test").info("project info")
    logging.getLogger("apache_beam.test").info("beam detail")
    logging.getLogger("apache_beam.test").error("beam failure")

    terminal = capsys.readouterr().err
    technical = log_path.read_text(encoding="utf-8")
    assert "project info" in terminal
    assert "beam detail" not in terminal
    assert "beam failure" in terminal
    assert "beam detail" in technical
    assert "beam failure" in technical


def test_verbose_shows_beam_info_in_terminal(tmp_path, capsys):
    log_path = tmp_path / "pipeline.log"
    configure_logging(verbose=True, log_path=log_path)
    logging.getLogger("apache_beam.test").info("beam detail verbose")

    assert "beam detail verbose" in capsys.readouterr().err


def test_stage_summary_reports_empty_output(capsys):
    run_all_module._print_stage_summary(
        "Bronze → Silver",
        {
            "status": "success",
            "duration_seconds": 0.0,
            "input_records": 2,
            "output_records": 0,
            "rejected_records": 2,
            "output_paths": [],
        },
    )

    terminal = capsys.readouterr().out
    assert "Registros gravados: 0" in terminal
    assert "Registros rejeitados: 2" in terminal
    assert "Caminho principal: nenhum" in terminal


def test_run_all_prints_report_driven_success_summary(tmp_path, monkeypatch, capsys):
    bronze = tmp_path / "states_abc_1.jsonl"
    silver = tmp_path / "aircraft_states-abc.parquet"
    gold = tmp_path / "latest_aircraft_states-abc.jsonl"
    bronze.write_text("{}\n", encoding="utf-8")
    for path in (silver, gold):
        path.touch()
    reports = {
        "collector": tmp_path / "collector.json",
        "bronze_to_silver": tmp_path / "silver.json",
        "silver_to_gold": tmp_path / "gold.json",
    }
    _write_report(reports["collector"], "collector", str(bronze), 12)
    _write_report(reports["bronze_to_silver"], "bronze_to_silver", str(silver), 10, 2)
    _write_report(reports["silver_to_gold"], "silver_to_gold", str(gold), 10)
    monkeypatch.setattr(run_all_module, "LOG_PATH", tmp_path / "pipeline.log")
    monkeypatch.setattr(
        run_all_module,
        "parse_args",
        lambda: Namespace(
            lat_min=-24.2,
            lon_min=-47.2,
            lat_max=-22.7,
            lon_max=-45.5,
            interval_seconds=1,
            max_collections=1,
            output=str(tmp_path),
            verbose=False,
        ),
    )
    monkeypatch.setattr(
        run_all_module, "collect_run", lambda: str(reports["collector"])
    )
    monkeypatch.setattr(
        run_all_module, "bronze_to_silver_run", lambda: str(reports["bronze_to_silver"])
    )
    monkeypatch.setattr(
        run_all_module, "silver_to_gold_run", lambda: str(reports["silver_to_gold"])
    )

    assert run_all_module.main() == 0
    terminal = capsys.readouterr().out
    assert "Pipeline concluído" in terminal
    assert "Coletados: 12" in terminal
    assert "Silver válidos: 10" in terminal
    assert "Rejeitados: 2" in terminal
    assert "Gold atualizado: sim" in terminal


def test_run_all_returns_failure_and_logs_traceback(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "pipeline.log"
    monkeypatch.setattr(run_all_module, "LOG_PATH", log_path)
    monkeypatch.setattr(
        run_all_module,
        "parse_args",
        lambda: Namespace(
            lat_min=-24.2,
            lon_min=-47.2,
            lat_max=-22.7,
            lon_max=-45.5,
            interval_seconds=1,
            max_collections=1,
            output=str(tmp_path),
            verbose=False,
        ),
    )
    monkeypatch.setattr(
        run_all_module,
        "collect_run",
        lambda: (_ for _ in ()).throw(RuntimeError("OpenSky indisponível")),
    )

    assert run_all_module.main() == 1
    terminal = capsys.readouterr()
    assert "Falha na etapa: coleta" in terminal.out
    assert "Log técnico:" in terminal.out
    assert "Traceback" not in terminal.err
    technical = log_path.read_text(encoding="utf-8")
    assert "OpenSky indisponível" in technical
    assert "Traceback" in technical
