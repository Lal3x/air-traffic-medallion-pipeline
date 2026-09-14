# Instalação e ambiente

## Pré-requisitos

- Python 3.13 (o projeto exige `>=3.13,<3.14`).
- Poetry com suporte ao formato `[dependency-groups]` do `pyproject.toml`.
- Git e acesso à internet para instalar dependências e consultar a OpenSky.
- Bash e Make para usar os atalhos do `Makefile`; no Windows, os exemplos de shell podem ser executados no WSL.

## Preparar o projeto

```bash
git clone https://github.com/Lal3x/air-traffic-medallion-pipeline.git
cd air-traffic-medallion-pipeline
poetry env use python3.13
poetry install --with dev
cp .env.example .env
```

Se já clonou o repositório, execute os comandos a partir de `poetry env use` na raiz do projeto. Copie `.env.example` apenas se ainda não tiver seu `.env`.

## Verificar o ambiente

```bash
poetry run python --version
poetry check
poetry run task check
poetry run task docs
```

`task check` executa lint, verificação de formatação, Mypy e testes com cobertura mínima de 70%. Os testes usam fixtures e mocks para as requisições OpenSky. `task docs` gera o site em `site/` com validação estrita.

## Como configurar a execução

O projeto possui uma classe `Settings` que lê `.env`, mas os comandos também passam valores explicitamente. Por isso, editar `.env` não altera todos os parâmetros da CLI.

| Parâmetro | Como configurar os comandos atuais |
| --- | --- |
| Região | `--lat-min`, `--lon-min`, `--lat-max`, `--lon-max` |
| Quantidade e intervalo | `--max-collections` e `--interval-seconds` |
| Destino Bronze | `--output` |
| URL da API e timeout | Variáveis exportadas `OPENSKY_API_BASE_URL` e `OPENSKY_REQUEST_TIMEOUT_SECONDS` |
| Entradas e saídas Silver/Gold | Argumentos das etapas; consulte seus guias |

O coletor lê URL e timeout diretamente com `os.getenv` e passa os resultados para `Settings`. Para alterá-los, exporte as variáveis no terminal; defini-las somente em `.env` não substitui esses valores. Os argumentos da CLI também prevalecem sobre as configurações de região, quantidade, intervalo e Bronze do `.env`.

```bash
export OPENSKY_REQUEST_TIMEOUT_SECONDS=45
poetry run python -m air_traffic_beam.run_all --max-collections 1 --interval-seconds 1
```

## Pre-commit

Instale o hook em cada clone em que desejar validação automática:

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

Os hooks verificam imports e formatação com Ruff, YAML/TOML, conflitos e espaços em branco, e executam toda a suíte com cobertura mínima de 70%. Quando um hook corrigir arquivos, revise as mudanças e use `git add` novamente antes de repetir o commit.

## Dados locais

As etapas criam os diretórios de saída conforme necessário:

```text
data/
  bronze/
  silver/
  gold/
  rejected/
  observability/
```

Dados gerados, `.env`, `.venv`, `.vscode`, cobertura e `site/` são ignorados pelo Git. As fixtures em `tests/fixtures/` permanecem versionadas.

Continue em [Execução local](running.md).
