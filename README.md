# Brazil Air Traffic Beam

## Objetivo

Este projeto implementa um pipeline local de dados para monitoramento do tráfego aéreo sobre a região de São Paulo, usando Apache Beam e arquitetura medalhão. A fonte primária é a API pública da OpenSky Network, acessada anonimamente sem cliente ID, client secret, token ou conta.

A estrutura atual executa localmente com `DirectRunner` e organiza os dados em Bronze, Silver e uma etapa posterior de Gold, sem anunciar suporte a Dataflow, S3 ou streaming em produção.

## Arquitetura

- Bronze: coleta JSONL da API OpenSky com metadata de execução e bounding box.
- Silver: transformação dos state vectors para registros normalizados e validados.
- Gold: uma visão atual por aeronave e um resumo agregado do tráfego.

## Bounding box utilizada

A API é consultada com a região de São Paulo definida por:

- `lat_min=-24.2`
- `lon_min=-47.2`
- `lat_max=-22.7`
- `lon_max=-45.5`

## Variáveis de ambiente

Crie um arquivo `.env` a partir do arquivo `.env.example` com as configurações a seguir:

```dotenv
OPENSKY_API_BASE_URL=https://opensky-network.org/api
OPENSKY_LAT_MIN=-24.2
OPENSKY_LON_MIN=-47.2
OPENSKY_LAT_MAX=-22.7
OPENSKY_LON_MAX=-45.5
OPENSKY_REQUEST_TIMEOUT_SECONDS=30
OPENSKY_INTERVAL_SECONDS=60
OPENSKY_MAX_COLLECTIONS=5
BRONZE_BASE_PATH=data/bronze
```

O arquivo `.env` é ignorado pelo Git. As variáveis antigas da SPTrans podem ser removidas manualmente.

## Coleta anônima

A coleta usa o endpoint público:

```text
GET https://opensky-network.org/api/states/all
```

Os limites geográficos são enviados como query parameters e a execução é finita e controlada por `--max-collections`.

### Comando de coleta

```bash
poetry run python -m air_traffic_beam.collectors.aircraft_states \
  --max-collections 5 \
  --interval-seconds 60
```

Também é possível definir um diretório de saída diferente com `--output`.

### Exemplo de saída Bronze

```text
data/bronze/aircraft_states/
  ingestion_date=YYYY-MM-DD/
    hour=HH/
      microbatch_<execution_id>.jsonl
```

    Cada arquivo representa uma execução de coleta e cada linha contém um envelope com `_metadata` e `payload`.
O `payload` é mantido como a resposta da API, sem renomear ou limpar campos. Respostas com `states: null` são tratadas de forma controlada no processamento, mas a camada Bronze preserva o payload original.

## Pipeline Bronze → Silver

```bash
poetry run python -m air_traffic_beam.pipelines.bronze_to_silver \
  --runner=DirectRunner \
  --direct_num_workers=1
```

O pipeline lê o envelope da Bronze, expande os state vectors da OpenSky, valida campos, normaliza `callsign`, converte unidades e grava registros válidos em Parquet e os rejeitados em JSONL.

### Saídas esperadas

```text
data/silver/aircraft_states/
data/rejected/aircraft_states/
```

## Pipeline Silver → Gold

O Gold lê todos os arquivos Parquet da Silver e produz duas visões em JSONL:

- `data/gold/latest/`: uma observação mais recente por `icao24`, usando `last_contact`.
- `data/gold/traffic/`: contagem de observações, aeronaves únicas, aeronaves no ar/no solo, velocidade média, altitude média e último contato.

```bash
poetry run python -m air_traffic_beam.pipelines.silver_to_gold \
  --runner=DirectRunner \
  --direct_num_workers=1
```

O processamento usa `ReadAllFromParquet` e permanece compatível com execução local no DirectRunner.

## Observabilidade

O terminal mostra somente as fases, métricas e mensagens INFO do pacote do projeto. O log técnico completo, incluindo INFO do Apache Beam e do Prism, fica em `data/observability/logs/pipeline.log` e usa rotação de 5 MB com três backups. Exceções e tracebacks são preservados nesse arquivo; erros importantes continuam visíveis no terminal.

Cada execução do coletor, Bronze → Silver e Silver → Gold grava um relatório JSON em `data/observability/`. Os relatórios incluem status, duração, quantidade de entradas e saídas, rejeições, taxa de erro e caminhos dos artefatos. A aba `Qualidade` do dashboard apresenta esses relatórios junto do resumo Gold.

Os sinks Bronze, Silver e Gold usam prefixos com UUID de execução. Assim, uma nova execução não apaga resultados anteriores e os relatórios contabilizam somente os artefatos produzidos naquela execução.

Para exibir também os logs INFO internos do Beam e do Prism no terminal:

```bash
poetry run python -m air_traffic_beam.run_all --verbose
```

Para manter uma execução contínua em micro-batches de cinco minutos:

```bash
make stream
```

Esse comando executa cinco coletas por ciclo, processa Bronze → Silver → Gold, atualiza o snapshot do dashboard e aguarda `300` segundos antes da próxima carga. O intervalo entre ciclos pode ser alterado com `make stream STREAM_INTERVAL_SECONDS=60`; a quantidade de coletas com `make stream STREAM_MAX_COLLECTIONS=10`. Interrompa com `Ctrl+C`; uma falha encerra o loop para evitar novas cargas incompletas.

## Estrutura dos dados

Cada state vector da OpenSky segue a ordem oficial:

```text
0  icao24
1  callsign
2  origin_country
3  time_position
4  last_contact
5  longitude
6  latitude
7  baro_altitude
8  on_ground
9  velocity
10 true_track
11 vertical_rate
12 sensors
13 geo_altitude
14 squawk
15 spi
16 position_source
17 category
```

## Observações de uso

- A API OpenSky pode responder `HTTP 429` quando o limite de uso anônimo é excedido.
- O código trata `429` separadamente e não reaplica a requisição imediatamente.
- `X-Rate-Limit-Remaining` e `Retry-After` são lidos quando disponíveis.
- O pipeline atual executa localmente com `DirectRunner`, sem depender de Dataflow, S3 ou streaming real.

## Comandos principais

```bash
poetry install
poetry check
poetry run task check
```

As tarefas disponíveis podem ser consultadas com `poetry run task --list`. Os comandos individuais incluem `task test`, `task lint`, `task format`, `task types` e `task docs`.

`poetry run task tests` (ou `task test`) executa os testes com cobertura do pacote `air_traffic_beam`, mostra as linhas não cobertas e gera `coverage.xml`. A cobertura mínima exigida é de 70%, tanto localmente quanto no CI. `task lint` verifica o código, a ordem dos imports e a formatação com Ruff; `task format` organiza os imports e formata o código.

Para habilitar a validação automática antes de cada commit, execute o comando dentro de um repositório Git:

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Dashboard

```bash
poetry run streamlit run src/air_traffic_beam/dashboard/app.py
```

O painel prioriza a visão Gold mais recente, com filtros por país e situação da aeronave, KPIs, mapa, tabela formatada e histórico de qualidade das execuções.

## Documentação no GitHub Pages

O CI valida a documentação com `poetry run mkdocs build --strict` em pull requests e pushes para `main` ou `master`. Após todas as verificações passarem, as execuções na branch padrão publicam o site no [GitHub Pages](https://lal3x.github.io/air-traffic-medallion-pipeline/). Também é possível iniciar o workflow `CI` manualmente pela aba **Actions**, selecionando a branch padrão.

Para habilitar a publicação, configure **Settings → Pages → Build and deployment → Source → GitHub Actions** no repositório. O workflow usa o `GITHUB_TOKEN`, sem necessidade de um token pessoal.

## Guias de estudo

- [Walkthrough completo do projeto](docs/project_walkthrough.md)
- [Apache Beam explicado no contexto deste código](docs/apache_beam_explained.md)

## Pastas e módulos

```text
src/
└── air_traffic_beam/
    ├── __init__.py
    ├── collectors/
    │   ├── __init__.py
    │   ├── opensky_client.py
    │   └── aircraft_states.py
    ├── pipelines/
    │   ├── __init__.py
    │   ├── hello_beam.py
    │   └── bronze_to_silver.py
    ├── transforms/
    │   ├── __init__.py
    │   └── aircraft_states.py
    ├── schemas/
    │   ├── __init__.py
    │   └── silver.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── observability/
    │   └── __init__.py
    └── exceptions.py
```
# air-traffic-medallion-pipeline
