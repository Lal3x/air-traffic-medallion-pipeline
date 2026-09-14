# Dúvidas e diagnóstico

## Preciso configurar um token?

O cliente deste projeto consulta `/states/all` sem enviar credenciais. Se a API recusar ou limitar a requisição, consulte o status HTTP e a mensagem registrada; não há fluxo de autenticação implementado.

## Por que há Bronze, Silver e Gold?

Bronze guarda respostas e contexto de ingestão; Silver valida e normaliza observações; Gold prepara visões para consumo. A separação permite inspecionar a origem de um resultado e reprocessar entradas selecionadas.

## Alterei o `.env`, mas a coleta não mudou. Por quê?

Os argumentos e defaults da CLI são passados explicitamente para `Settings`. Use as flags para região, quantidade, intervalo e destino Bronze. URL e timeout devem ser exportados no ambiente do processo. Veja [Instalação e ambiente](setup.md).

## Recebi HTTP 429. O que fazer?

O coletor encerra sem repetir imediatamente. Consulte o tempo de espera informado na mensagem, aguarde antes de reiniciar e ajuste o intervalo/quantidade de coletas. Se já recebeu respostas válidas, procure um arquivo `_partial.jsonl` e o relatório de falha.

## O dashboard está vazio ou desatualizado

Execute uma carga completa com `make run` e clique em **Atualizar dados**. Confira os arquivos Gold e seus horários de modificação. Uma resposta sem aeronaves ou uma carga só com rejeições pode produzir uma visão vazia. Abrir o dashboard não inicia coleta nem atualização periódica.

## O Gold diz que não encontrou Parquet Silver

Execute Bronze → Silver antes e confira o caminho de `--input`. A opção mais simples para a primeira carga é `make run`, que encadeia as três etapas.

## Por que as contagens aumentam quando repito as etapas?

As etapas isoladas leem o histórico por padrão e preservam saídas anteriores. Reprocessar a mesma Bronze cria novas observações Silver. Use `run_all` para processar a carga atual ou selecione os arquivos com `--input`.

## Onde ficam os rejeitados?

Em `data/rejected/aircraft_states/`, em JSONL com `rejection_reason`. O formato está no [dicionário de dados](data_dictionary.md).

## Qual fuso é usado?

`last_contact` e outros epochs preservam o instante em segundos Unix. `last_contact_at`, metadados operacionais e apresentação no dashboard usam `America/Sao_Paulo`.

## Um relatório com sucesso garante que a última tentativa funcionou?

Não. Uma falha pode ocorrer antes da gravação de um novo relatório. Compare o horário do JSON com o log e o código de saída; veja [Logs e relatórios](reports.md).

## O commit falhou por cobertura ou formatação

Execute `poetry run task tests` para consultar as linhas não cobertas; o mínimo é 70%. Para formatação, use `poetry run task format`, revise e adicione os arquivos novamente. Depois, execute `poetry run pre-commit run --all-files`.

## Como visualizar e publicar a documentação?

Use `poetry run mkdocs serve` para abrir o site local e `poetry run task docs` para validar o build. O CI publica no GitHub Pages após passar na branch padrão; a fonte de publicação deve estar configurada como **GitHub Actions** nas configurações de Pages. Pull requests validam a documentação sem publicá-la.
