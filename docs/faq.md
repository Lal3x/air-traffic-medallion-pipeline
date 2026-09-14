# FAQ

## A API requer token?

Não. Este projeto usa a API pública da OpenSky Network, que pode ser acessada sem token para consulta de dados públicos.

## Por que o projeto usa Bronze, Silver e Gold?

Para separar os dados brutos, os dados limpos e as visões analíticas. Isso facilita manutenção, depuração e estudo da arquitetura.

## Qual runner é usado?

Durante o desenvolvimento e execução local, o projeto usa `DirectRunner`.

## Onde ficam os dados de rejeição?

Em diretórios sob `data/rejected/` e em arquivos JSONL por etapa.

## O projeto usa tempo UTC ou horário de São Paulo?

O projeto foi ajustado para manter o fuso de São Paulo em contextos operacionais e de apresentação.
