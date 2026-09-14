# Observabilidade

O projeto registra logs técnicos e relatórios JSON com contagens obtidas dos artefatos produzidos. As métricas de negócio são calculadas após a gravação; não são contadores `Metrics.counter` do Beam.

## Onde ficam os artefatos

```text
data/observability/
  collector-<uuid>.json
  bronze_to_silver-<uuid>.json
  silver_to_gold-<uuid>.json
  logs/
    pipeline.log
```

O arquivo de log é configurado pelo orquestrador `run_all`. Os relatórios preservam o histórico de cada etapa, enquanto o log possui rotação.

## Investigar uma execução

1. Confira o código de saída e a etapa indicada no terminal.
2. Consulte `data/observability/logs/pipeline.log` se executou com `run_all`.
3. Compare os horários e `output_paths` dos relatórios com os arquivos da carga.
4. Inspecione os rejeitados JSONL em `data/rejected/aircraft_states/`.
5. Use a aba **Qualidade** do dashboard para consultar o histórico.

Veja [Logs e relatórios](reports.md) para os campos reais, as unidades das contagens e os casos em que uma falha não produz relatório.
