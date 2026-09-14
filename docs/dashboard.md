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

O dashboard lê os artefatos mais recentes da pasta Gold e usa o horário de modificação do arquivo para selecionar o snapshot atual. Isso evita assumir que o nome do arquivo contém a data mais recente.

## Boas práticas

- mantenha o dashboard como leitura somente;
- deixe os arquivos Gold em diretórios separados por objetivo;
- use relatórios JSON para diagnóstico, não como fonte principal de análise.
