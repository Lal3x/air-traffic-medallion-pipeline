# Coleta da OpenSky

A coleta é feita por um cliente Python que consulta o endpoint público da OpenSky Network.

## Comando

```bash
poetry run python -m air_traffic_beam.collectors.aircraft_states \
  --max-collections 3 \
  --interval-seconds 60
```

## O que é coletado

O endpoint retorna uma lista de states com dados de aeronaves em uma região geográfica.

Cada resposta fica armazenada em um envelope com:

- metadados da execução;
- bounding box aplicado;
- timestamp local de São Paulo;
- payload bruto da OpenSky.

## Nome do arquivo

Os arquivos são gerados com padrão semelhante a:

```text
data/bronze/aircraft_states/ingestion_date=2026-09-14/hour=12/microbatch_<execution_id>.jsonl
```

Cada linha representa uma requisição da execução. Isso reduz a quantidade de arquivos sem perder a granularidade das respostas individuais.

## Observações

- a API pública pode responder 429;
- a rotina não expõe token algum;
- o uso é local e controlado por contador de coletas.
