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
data/gold/latest/latest_aircraft_states-<run_id>-00000-of-00001.jsonl
```

Representa a última observação por aeronave, escolhida pelo maior `last_contact`.

### Traffic

```text
data/gold/traffic/traffic_summary-<run_id>-00000-of-00001.jsonl
```

Contém agregados como:

- aeronaves observadas;
- aeronaves únicas;
- número de observações em voo;
- número de observações no solo;
- velocidade média;
- altitude média;
- último contato observado.

## Como a agregação funciona

1. Leitura da Silver em Parquet;
2. agrupamento por `icao24`;
3. seleção do registro mais recente;
4. resumo calculado em uma ramificação independente, sobre todas as observações de entrada;
5. gravação em JSONL por execução.

## Observabilidade

Assim como nas outras etapas, o Gold registra um relatório JSON com status, arquivos produzidos e contagens reais.

## Escopo da carga

`--input` aceita um diretório, arquivo Parquet ou padrão. O padrão é ler todos os Parquets sob `data/silver/aircraft_states`. O orquestrador `run_all` passa somente a Silver recém-produzida.

Os argumentos `--latest-output` e `--summary-output` definem prefixos de saída. UUID e sufixo de shard são acrescentados automaticamente.

`latest` deduplica por aeronave, mas `traffic` inclui observações repetidas. Não há janela temporal Beam nem filtro de idade das posições: a visão depende dos arquivos selecionados. Consulte o [dicionário](data_dictionary.md) para a definição de cada agregado.
