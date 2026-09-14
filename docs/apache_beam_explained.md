# Apache Beam explicado neste projeto

Este guia relaciona conceitos do Apache Beam com arquivos reais do repositório. O objetivo é entender o modelo de programação antes de trocar o runner local por uma infraestrutura distribuída.

## Pipeline

Uma `Pipeline` é o grafo de leitura, transformação e escrita. Em `pipelines/bronze_to_silver.py`:

```python
with beam.Pipeline(options=options) as pipeline:
    lines = pipeline | "Ler arquivos Bronze" >> beam.io.ReadFromText(input_path)
```

O bloco constrói e executa o grafo. As transformações não devem ser confundidas com chamadas Python imediatas: o Beam registra operações que serão executadas pelo runner.

## Runner

O Runner executa o grafo. Este projeto usa `PipelineOptions` com `DirectRunner`, adequado para desenvolvimento local e lotes pequenos. O DirectRunner pode usar o Prism como componente local do Apache Beam.

Dataflow é outro runner: é um serviço gerenciado do Google Cloud que executa grafos Beam com recursos distribuídos. Beam define o pipeline; Dataflow, DirectRunner e outros runners definem onde e como ele roda. Este projeto não depende de Dataflow.

## Prism e DirectRunner

Prism aparece nos logs como parte do caminho local moderno do DirectRunner. Ele não é uma nova camada de dados nem substitui o Beam. O log técnico registra detalhes de execução, enquanto o terminal mostra somente mensagens do projeto e erros importantes.

## PCollection

Uma `PCollection` é a coleção distribuída de elementos que passa entre transformações. Exemplos:

- `lines`: linhas JSONL Bronze;
- `parsed.valid`: observações de aeronaves já expandidas e normalizadas pelo parsing;
- `parsed.rejected`: tagged output de entradas inválidas;
- `normalized.valid`: registros Silver prontos para Parquet.

Uma PCollection pode ser grande. O pipeline deve operar elemento a elemento ou em bundles, em vez de carregar a entrada inteira em uma lista Python.

## PTransform

Uma PTransform é uma operação aplicada a uma PCollection. O operador `|` liga a entrada a uma transformação nomeada:

```python
normalized = parsed.valid | "Normalizar aeronaves" >> beam.ParDo(
    ValidateAndNormalizeAircraftState()
)
```

Os nomes tornam o grafo e os logs compreensíveis.

## ParDo e DoFn

`ParDo` aplica um `DoFn` a cada elemento. Os `DoFn` deste projeto estão em `transforms/aircraft_states.py`:

- `ParseEnvelope` lê JSON, encontra `payload.states` e expande um envelope em várias aeronaves;
- `ValidateAndNormalizeAircraftState` valida campos e normaliza um registro individual.

Um `DoFn.process()` pode emitir zero, um ou vários elementos. Isso é importante porque um envelope Bronze pode conter muitas aeronaves.

## Tagged outputs

`with_outputs(REJECTED_TAG, main="valid")` cria saídas nomeadas. O fluxo principal contém registros válidos; o tag `rejected` recebe o registro e o motivo da rejeição.

```python
parsed = lines | "Validar envelopes" >> beam.ParDo(ParseEnvelope()).with_outputs(
    REJECTED_TAG, main="valid"
)
```

Depois, os rejeitados do parsing e da validação são combinados com `Flatten` e gravados em JSONL. Essa estratégia evita esconder dados ruins e permite medir a qualidade do lote.

## Map

`beam.Map` aplica uma função simples a cada elemento. Em `silver_to_gold.py`, ele cria uma chave por aeronave:

```python
beam.Map(lambda record: (record["icao24"], record))
```

Também é usado para serializar registros e construir o resumo Gold.

## GroupByKey e combinação por chave

A Gold agrupa observações pelo `icao24`:

```python
| "Agrupar por aeronave" >> beam.Map(lambda record: (record["icao24"], record))
| "Combinar observações por aeronave" >> beam.GroupByKey()
```

O projeto seleciona a posição mais recente em `_latest_by_aircraft`. Isso é uma combinação por chave feita explicitamente sobre as observações de cada aeronave.

Em pipelines maiores, `CombinePerKey` costuma ser preferível quando existe um acumulador associativo e comutativo, pois permite combinar parcialmente os dados e reduzir memória/shuffle. O projeto usa `GroupByKey` para explicitar o agrupamento didaticamente. Selecionar um registro completo também pode ser implementado com um `CombineFn`, definindo um critério estável de desempate.

## Combine e agregações

A função `ToList` cria uma lista por PCollection para o resumo local. Isso é suficiente para o objetivo didático e para as cargas pequenas do DirectRunner, mas não é a melhor opção para uma fonte ilimitada ou muito grande.

Para escala maior, o resumo deveria usar combinações incrementais, como `Count`, `Mean`, `CombinePerKey` ou um `CombineFn` customizado. Essas operações evitam manter todos os registros em uma lista única.

## Leitura e escrita

As fontes e sinks do projeto são:

- `ReadFromText`: lê linhas Bronze;
- `WriteToParquet`: grava Silver tipada;
- `ReadAllFromParquet`: lê os arquivos Silver encontrados;
- `WriteToText`: grava Gold JSONL e rejeitados.

Cada sink recebe nome explícito e prefixo UUID. Assim, execuções diferentes não sobrescrevem os artefatos anteriores.

## Métricas e relatórios

As métricas de negócio não são um `Metrics.counter` do Beam: são relatórios JSON produzidos depois que os sinks terminam, usando contagem de linhas JSONL e metadata Parquet. Isso permite que o terminal e o dashboard exibam o resultado real do artefato concluído.

O módulo `observability/metrics.py` define o contrato do relatório. O módulo `observability/run_report.py` persiste o relatório. O módulo `logging_config.py` mantém os logs técnicos separados da saída resumida.

## Processamento em pequenos lotes

`make stream` executa o pipeline finito repetidamente. Cada ciclo coleta várias respostas, processa Bronze → Silver → Gold e aguarda o intervalo configurado. Isso é um micro-batch local.

Ele não é equivalente a um pipeline de streaming ilimitado: não usa janela, watermark, trigger ou estado persistente de streaming. Essas abstrações podem ser adicionadas quando houver uma fonte contínua e um runner adequado.

## Beam versus Dataflow

Apache Beam é o SDK e o modelo de programação portátil. Ele descreve PCollections e PTransforms. Dataflow é um serviço gerenciado que executa esse modelo em infraestrutura cloud.

Neste repositório:

- Beam: `src/air_traffic_beam/pipelines/` e `transforms/`;
- Runner local: `DirectRunner` configurado pelos comandos;
- armazenamento: filesystem local em `data/`;
- dashboard: Streamlit e DuckDB;
- equivalente futuro cloud: trocar opções do runner e os IOs, mantendo as transformações quando os contratos forem compatíveis.
