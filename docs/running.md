# Execução local

## Instalação

```bash
poetry install
```

## Coleta

```bash
poetry run python -m air_traffic_beam.collectors.aircraft_states --max-collections 1 --interval-seconds 1
```

## Bronze → Silver

```bash
poetry run python -m air_traffic_beam.pipelines.bronze_to_silver --runner=DirectRunner --direct_num_workers=1
```

## Silver → Gold

```bash
poetry run python -m air_traffic_beam.pipelines.silver_to_gold --runner=DirectRunner --direct_num_workers=1
```

## Execução complete

```bash
poetry run python -m air_traffic_beam.run_all --max-collections 1 --interval-seconds 1
```

## Dashboard

```bash
poetry run streamlit run src/air_traffic_beam/dashboard/app.py
```
