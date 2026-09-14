# Logs e relatórios

## Localização

Os relatórios são gravados diretamente em `data/observability/<pipeline>-<uuid>.json`, com `pipeline` igual a `collector`, `bronze_to_silver` ou `silver_to_gold`.

A execução por `run_all` configura o log técnico em `data/observability/logs/pipeline.log`, com rotação de 5 MB e três backups. O terminal mostra INFO do projeto e erros de bibliotecas; `--verbose` também exibe INFO de Beam/Prism. Os comandos isolados não configuram automaticamente esses mesmos handlers.

## Contrato do relatório

| Campo | Significado |
| --- | --- |
| `run_id` | UUID próprio do relatório, diferente do UUID dos arquivos de dados |
| `pipeline`, `status` | Etapa e resultado (`success` ou `failed`) |
| `started_at`, `finished_at` | Strings ISO 8601 com fuso de São Paulo |
| `duration_seconds` | Duração medida pela etapa |
| `input_files`, `input_records` | Arquivos e registros contados conforme a etapa |
| `output_records`, `rejected_records` | Registros de saída e rejeições |
| `missing_position_records` | Campo existente no modelo, atualmente não preenchido pelas etapas |
| `error_rate` | Razão calculada pela etapa Bronze → Silver; zero por padrão nas demais |
| `output_paths` | Caminhos dos artefatos de saída registrados pela etapa |
| `error_message` | Mensagem de falha ou nulo |

`started_at` é inicializado quando o objeto do relatório é criado, ao final do processamento. Portanto, use `duration_seconds` para a duração; a diferença entre `finished_at` e `started_at` não representa o tempo completo da etapa.

## Como interpretar as contagens

| Etapa | Entrada | Saída |
| --- | --- | --- |
| Coletor | Observações retornadas pela API na execução bem-sucedida | Observações contidas nos envelopes gravados |
| Bronze → Silver | Linhas JSONL, isto é, envelopes | Observações válidas em Parquet |
| Silver → Gold | Observações nos Parquets lidos | Registros da visão `latest`; o registro de resumo não entra nessa contagem |

Na Bronze → Silver, uma linha pode conter várias aeronaves. `error_rate` é `rejected_records / input_records`, portanto pode ultrapassar 1 e não deve ser interpretado como percentual de aeronaves inválidas. `output_paths` dessa etapa lista a Silver; os rejeitados ficam no destino configurado por `--rejected-output`.

## Falhas e histórico

O coletor registra `status=failed` quando uma falha ocorre dentro do bloco de coleta/gravação e preserva respostas anteriores em um arquivo parcial. Erros de configuração anteriores a esse bloco podem não gerar relatório.

As etapas Beam gravam relatórios após concluir o processamento. Se falharem antes disso, pode não haver novo JSON; consulte o log ou a saída do processo. Um relatório anterior com sucesso não comprova que a última tentativa terminou bem.

A aba **Qualidade** apresenta o relatório mais recente de cada etapa. Esses registros podem pertencer a execuções diferentes; compare horários e caminhos ao investigar uma carga.
