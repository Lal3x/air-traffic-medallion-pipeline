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
- payload da OpenSky, com `states: null` ou ausente convertido em lista vazia pelo cliente.

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

## Gravação e falhas

As respostas são acumuladas em memória e gravadas em um único arquivo ao final da execução, usando um arquivo temporário e renomeação atômica. Se uma requisição falhar após coletas válidas, o coletor salva essas respostas em `microbatch_<execution_id>_partial.jsonl`, registra a falha e encerra com erro.

Timeouts, erros de conexão e HTTP 5xx permitem até três tentativas no total. HTTP 429 não é repetido automaticamente: a mensagem inclui o tempo de espera quando disponível nos headers.

Sem argumentos, o coletor usa cinco coletas e intervalo de 60 segundos. O comando `run_all` usa uma coleta e intervalo de um segundo. Use os argumentos explícitos para evitar confundir esses padrões; veja [Configuração](setup.md).
