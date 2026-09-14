# Execução local

Execute os comandos na raiz do repositório, após seguir a [instalação](setup.md).

## Primeira carga completa

```bash
poetry run python -m air_traffic_beam.run_all --max-collections 1 --interval-seconds 1
```

O atalho equivalente é `make run`. A execução coleta uma resposta, transforma o arquivo Bronze recém-criado em Silver e usa a Silver dessa carga para produzir Gold. Uma falha interrompe a sequência e retorna código de saída diferente de zero.

Ao terminar, confira os arquivos em `data/bronze/aircraft_states/`, `data/silver/aircraft_states/`, `data/gold/latest/` e `data/gold/traffic/`. Os relatórios JSON ficam em `data/observability/`.

## Abrir o dashboard

Em outro terminal:

```bash
poetry run streamlit run src/air_traffic_beam/dashboard/app.py
```

Abra o endereço exibido pelo Streamlit, normalmente `http://localhost:8501`. O botão **Atualizar dados** recarrega os artefatos; abrir o painel não inicia uma coleta.

## Executar etapas separadas

```bash
poetry run python -m air_traffic_beam.collectors.aircraft_states --max-collections 1 --interval-seconds 1
poetry run python -m air_traffic_beam.pipelines.bronze_to_silver --runner=DirectRunner --direct_num_workers=1
poetry run python -m air_traffic_beam.pipelines.silver_to_gold --runner=DirectRunner --direct_num_workers=1
```

Os comandos isolados usam entradas históricas por padrão: Bronze → Silver lê o padrão `data/bronze/aircraft_states/**/*.jsonl`; Silver → Gold lê os Parquets sob `data/silver/aircraft_states`. Reprocessar a mesma Bronze cria novos arquivos Silver, e agregá-los junto aos anteriores pode contar observações repetidas.

Para limitar o processamento a uma carga, prefira `run_all` ou passe `--input` com o arquivo desejado. Consulte [Bronze → Silver](bronze_to_silver.md) e [Silver → Gold](silver_to_gold.md) para os argumentos de saída.

## Repetir a coleta em lotes

```bash
make stream
```

Por padrão, cada ciclo faz **15 coletas**, com **1 segundo** entre requisições, processa as três camadas e espera **300 segundos após o processamento**. O período total inclui o tempo de coleta e transformação.

Para usar três coletas espaçadas por 60 segundos:

```bash
make stream STREAM_MAX_COLLECTIONS=3 STREAM_COLLECTION_INTERVAL_SECONDS=60 STREAM_INTERVAL_SECONDS=300
```

Use `Ctrl+C` para parar. Uma falha encerra o loop. Em caso de HTTP 429, consulte o tempo de espera indicado pela API antes de reiniciar.

## Diagnóstico

```bash
poetry run python -m air_traffic_beam.run_all --verbose
```

O orquestrador grava logs técnicos em `data/observability/logs/pipeline.log`. Veja [Logs e relatórios](reports.md) para interpretar as contagens e as limitações dos relatórios.
