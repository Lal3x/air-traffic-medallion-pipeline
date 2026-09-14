# Bronze → Silver

A etapa Bronze → Silver transforma a resposta bruta em dados analíticos prontos para consumo.

## Etapas principais

1. leitura dos arquivos JSONL da Bronze;
2. parsing de cada envelope;
3. expansão do state vector em campos estruturados;
4. validação de coordenadas e identificadores;
5. conversão de velocidade e altitude;
6. gravação em Parquet para a Silver;
7. persistência de rejeitados em JSONL.

## Comando

```bash
poetry run python -m air_traffic_beam.pipelines.bronze_to_silver \
  --runner=DirectRunner \
  --direct_num_workers=1
```

## Registros válidos

A Silver guarda registros com schema tipado, incluindo:

- `icao24`
- `callsign`
- `origin_country`
- `last_contact`
- `last_contact_at`
- `latitude`
- `longitude`
- `velocity_kmh`
- `on_ground`

## Registros rejeitados

Os registros inválidos são gerados em JSONL para permitir auditoria e investigação posterior.

## Observabilidade

A etapa também grava um relatório em `data/observability/` com:

- duração;
- número de registros lidos;
- registros válidos;
- rejeitados;
- taxa de erro;
- caminhos de saída.
