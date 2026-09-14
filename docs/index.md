<div class="hero-panel">
    <div class="hero-kicker">PORTFÓLIO DE ENGENHARIA DE DADOS <span>•</span> APACHE BEAM</div>
    <h1>Brazil Air<br><em>Traffic Beam</em></h1>
    <p class="hero-lead">Um laboratório local de dados para transformar sinais de tráfego aéreo em uma história rastreável: coletar, validar, agregar e explicar.</p>
    <div class="hero-actions">
        <a class="md-button md-button--primary" href="setup/">Começar pelo setup</a>
        <a class="md-button" href="architecture/">Ver arquitetura</a>
    </div>
</div>

<div class="signal-grid">
    <div class="signal-card"><strong>01</strong><span>API pública<br>OpenSky</span></div>
    <div class="signal-card"><strong>02</strong><span>Medallion<br>Bronze → Gold</span></div>
    <div class="signal-card"><strong>03</strong><span>Execução<br>local observável</span></div>
</div>

## O projeto em uma leitura

Este projeto implementa um fluxo medallion em Python com:

- coleta da OpenSky Network em Bronze,
- validação e normalização em Silver,
- agregações e snapshot em Gold,
- observabilidade com relatórios JSON e logs técnicos,
- dashboard interativo em Streamlit.

## A ideia central

O principal objetivo é demonstrar, de forma didática, como um pipeline de dados pode ser estruturado com Apache Beam em um ambiente local, usando dados reais da API pública da OpenSky e preservando um histórico operacional sem sobrescrever resultados anteriores.

## Stack principal

- Python 3.13
- Apache Beam (DirectRunner)
- PyArrow
- DuckDB
- Streamlit
- Pydantic Settings
- Tenacity
- MkDocs + Material

## Fluxo principal

```mermaid
flowchart LR
    API[OpenSky API] --> COL[Coleta Bronze]
    COL --> SILVER[Silver: Parquet]
    SILVER --> GOLD[Gold: JSONL]
    GOLD --> DASH[Dashboard]
    COL --> REPORTS[Relatórios]
    SILVER --> REPORTS
    GOLD --> REPORTS
```

## Roteiro de estudo

1. [Prepare o ambiente](setup.md) e entenda as configurações locais.
2. [Execute a coleta](collection.md) e observe um microbatch Bronze.
3. [Siga a transformação Bronze → Silver](bronze_to_silver.md).
4. [Explore o Gold e o dashboard](silver_to_gold.md).
5. [Leia o walkthrough de Beam](project_walkthrough.md) para conectar código e conceitos.

## Documentação relacionada

- [Arquitetura](architecture.md)
- [Fluxo de dados](data_flow.md)
- [Guia de execução](setup.md)
- [Apache Beam explicado](apache_beam_explained.md)

!!! tip "Uma boa primeira exploração"
    Rode uma execução pequena, abra os arquivos em `data/` e compare o payload bruto da Bronze com o registro normalizado da Silver. A arquitetura fica mais clara quando você acompanha a mesma aeronave pelas três camadas.
