# Logs e relatórios

Cada etapa do pipeline pode emitir um relatório de execução em JSON.

## Estrutura sugerida

```json
{
  "run_id": "2026-09-14T12:00:00-03:00",
  "stage": "silver_to_gold",
  "records_read": 120,
  "records_written": 89,
  "records_rejected": 31,
  "status": "success"
}
```

## Quando consultar

- antes de diagnosticar um erro de pipeline;
- ao comparar duas execuções;
- ao confirmar se a coleta está gerando volume esperado;
- ao validar a última snapshot Gold.

## Boa prática

Atenção especial para a linguagem de tempo: o projeto usa o fuso de São Paulo para manter a linha do tempo consistente com a operação local e a leitura em dashboard.
