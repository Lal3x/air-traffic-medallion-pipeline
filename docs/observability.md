# Observabilidade

A observabilidade do projeto foi desenhada para apoiar estudo e depuração local sem esconder falhas reais.

## O que é coletado

- logs de execução do projeto;
- métricas do pipeline Beam;
- número de registros por etapa;
- arquivos gerados em Bronze, Silver e Gold;
- indicadores de rejeição e sucesso.

## Onde ficam os artefatos

```text
data/
  observability/
    run_reports/
    logs/
```

## Filosofia

A ideia não é ocultar erros com mensagens genéricas. O projeto mantém logs úteis e detalhados, mas com filtros que evitam poluição excessiva no terminal.

## Recomendação

Para investigar uma falha, use:

1. o log técnico em arquivo;
2. o relatório de execução JSON;
3. os arquivos rejectados;
4. o dashboard como validação visual.
