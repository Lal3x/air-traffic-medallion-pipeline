# Dashboard

O dashboard é uma camada visual sobre os dados Gold.

## Como abrir

```bash
poetry run streamlit run src/air_traffic_beam/dashboard/app.py
```

## O que ele mostra

- aeronaves mais recentes observadas;
- estado atual do tráfego aéreo;
- contagem por condição (em voo ou no solo);
- estatísticas de velocidade e altitude;
- contexto de origem da última execução.

## Estratégia de leitura

O dashboard escolhe, separadamente, o arquivo `latest` e o arquivo `traffic` mais recentes pelo horário de modificação. Se não houver arquivo `latest` Gold, consulta Parquets Silver com DuckDB como alternativa; nessa leitura, não há deduplicação por aeronave.

O painel carrega até 500 registros antes de aplicar os filtros por país, categoria e situação. Os KPIs do topo refletem essa seleção; o resumo da aba **Qualidade** representa todas as observações processadas em Gold.

O cache tem validade de 30 segundos, mas isso não agenda atualização automática da página. Use **Atualizar dados** para limpar o cache e recarregar. O painel não executa o pipeline. Os dados representam as observações dos arquivos escolhidos, sem garantia de que as posições ainda sejam atuais.

## Boas práticas

- mantenha o dashboard como leitura somente;
- deixe os arquivos Gold em diretórios separados por objetivo;
- use relatórios JSON para diagnóstico, não como fonte principal de análise.
