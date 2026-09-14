# Introdução

Este projeto foi pensado como uma referência didática para pipelines de dados locais com Apache Beam, usando uma API pública de monitoramento aéreo.

A camada Bronze preserva a resposta original da OpenSky Network. A camada Silver converte cada vetor posicional em um registro estruturado, validado e pronto para análise. A camada Gold agrega a visão mais recente por aeronave e também gera um resumo do tráfego.

## Principais características

- coleta pública e sem autenticação para a OpenSky Network;
- estratégia de microbatch por execução local;
- arquivos sendo persistidos por execução, sem apagar históricos;
- biblioteca de observabilidade com JSON de execução e logs técnicos;
- dashboard para verificar o estado atual do mercado de tráfego aéreo;
- organização clara de pastas para Bronze, Silver, Gold e observabilidade.

## Regras de negócio

- O fuso usado nas leituras e nos artefatos de tempo é o de São Paulo.
- Cada execução gera identidades únicas para rastreio de histórico.
- Registros inválidos são guardados em rejeitados para auditoria.
- Dados Gold são separados em `latest` e `traffic`.

## Arquitetura em resumo

```mermaid
flowchart TD
    API[OpenSky Network] --> BRONZE[Bronze: JSONL]
    BRONZE --> SILVER[Silver: Parquet]
    SILVER --> GOLD[Gold: JSONL]
    GOLD --> DASH[Streamlit Dashboard]
    BRONZE --> REJECTED[Rejeitados]
    BRONZE --> REPORTS[Relatórios]
    SILVER --> REPORTS
    GOLD --> REPORTS
```
