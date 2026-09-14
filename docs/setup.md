# Instalação e ambiente

## Pré-requisitos

- Python 3.13
- Poetry
- Git
- Ambiente Linux/macOS/Windows com terminal compatível

## Instalação

```bash
poetry install
```

## Verificar ambiente

```bash
poetry run python --version
poetry run pytest -q
```

## Configuração de ambiente

O projeto usa um arquivo `.env` para ajustes de execução local. Caso ainda não exista, crie baseado no `.env.example`.

Exemplo:

```env
OPENSKY_API_BASE_URL=https://opensky-network.org/api
OPENSKY_LAT_MIN=-24.2
OPENSKY_LON_MIN=-47.2
OPENSKY_LAT_MAX=-22.7
OPENSKY_LON_MAX=-45.5
OPENSKY_REQUEST_TIMEOUT_SECONDS=30
OPENSKY_INTERVAL_SECONDS=60
OPENSKY_MAX_COLLECTIONS=5
```

## Estrutura de dados local

```text
data/
  bronze/
  silver/
  gold/
  rejected/
  observability/
```
