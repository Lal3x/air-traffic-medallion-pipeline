# Arquitetura

```mermaid
flowchart TD
    API["OpenSky API"] --> Collector["Coletor Python"]
    Collector --> Bronze["Bronze: JSONL"]
    Bronze --> Beam1["Beam: validação e normalização"]
    Beam1 --> Silver["Silver: Parquet"]
    Beam1 --> Rejected["Rejeitados: JSONL"]
    Silver --> Beam2["Beam: agregações"]
    Beam2 --> Gold["Gold: Parquet"]
    Gold --> DuckDB["DuckDB"]
    DuckDB --> Streamlit["Streamlit"]
    Beam1 --> Obs["Relatórios e métricas"]
    Beam2 --> Obs
    Obs --> Streamlit
```

A coleta usa `DirectRunner` localmente e salva cada resposta em Bronze imediatamente. O pipeline de transformação normaliza os state vectors e separa registros inválidos. O dashboard lê apenas os arquivos relevantes com DuckDB, aplicando filtros e limites antes de converter para pandas.
