# Silver → Gold

A camada Gold transforma a Silver em uma visão operacional útil para dashboards e análises curtas.

## Comando

```bash
poetry run python -m air_traffic_beam.pipelines.silver_to_gold \
  --runner=DirectRunner \
  --direct_num_workers=1
```

## Visões geradas

### Latest

```text
data/gold/latest/latest_aircraft_states-<run_id>.jsonl
```

Representa a última observação por aeronave, escolhida pelo maior `last_contact`.

### Traffic

```text
data/gold/traffic/traffic_summary-<run_id>.jsonl
```

Contém agregados como:

- aeronaves observadas;
- aeronaves únicas;
- número de aeronaves em voo;
- número no solo;
- velocidade média;
- altitude média;
- último contato observado.

## Como a agregação funciona

1. Leitura da Silver em Parquet;
2. agrupamento por `icao24`;
3. seleção do registro mais recente;
4. resumo por lote;
5. gravação em JSONL por execução.

## Observabilidade

Assim como nas outras etapas, o Gold registra um relatório JSON com status, arquivos produzidos e contagens reais.
