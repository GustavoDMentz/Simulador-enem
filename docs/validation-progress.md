# Restauração do PR #2

Escopo concluído: recuperar as 59 questões do checkpoint `09df6b5`, sem iniciar
nova auditoria das 454 restantes. O conflito documental com a main foi resolvido
somente na branch do PR; a main e a produção não foram alteradas.

## Recuperação verificável

As duas partes foram recuperadas dos anexos anteriores. O ZIP reconstruído tem
579.094.830 bytes e passou novamente em `unzip -t` antes da extração.
SHA-256: `a2efb083c95057b71f698e25cd11da031703b2f7da4bd50d3d7e8dbe82371a97`.
Foram inspecionadas 8.908 entradas, sem caminhos de travessia ou duplicados;
nove links simbólicos foram excluídos. Extraíram-se apenas 37 PDFs e o manifesto
oficial de origem, em diretório isolado, sem executar código do arquivo.

O arquivo contém o checkout c268020, anterior ao checkpoint remoto. Os commits
locais históricos 21dbcd7, 935291f e 636a80e não estavam disponíveis no GitHub;
seus componentes necessários foram reconstruídos e testados novamente.

## Resultado

- 59 registros restaurados com hashes de conteúdo idênticos ao checkpoint.
- 59 gabaritos reconferidos nos PDFs cujo SHA-256 coincide com a evidência.
- 12 imagens restauradas por renderização direta dos PDFs e inspecionadas.
- 513 questões na prévia; exatamente 454 pendentes preservadas sem alterações.
- Apenas as 59 aprovações explícitas são elegíveis à correção no simulador/API.
- TRI não é presumida: a API e a publicação retornam `parametros_tri: null`.

`data/audit/restoration-verification.json` registra a verificação de cada questão.
O manifesto ativo vincula identidade, conteúdo, alternativas, resposta, evidência
de gabarito e hash do arquivo de imagem. Ausência ou alteração de dependências
retira a questão correspondente da pontuação. Manifesto ilegível bloqueia a API.
As evidências históricas e a cópia de recuperação permanecem intactas.

Os apoios complexos foram preservados em PNG, incluindo textos e créditos:
esses trechos não são selecionáveis e a descrição alternativa é genérica.
Esta restauração não certifica TRI nem as 454 questões pendentes.

## Repetir os checks

```bash
npm install --prefix web --ignore-scripts --no-audit --no-fund
python scripts/publish_blue_candidates.py
python -m compileall -q scripts
python -m pytest -q tests scripts/tests
node --test web/tests/*.test.js
python scripts/audit_fused_db.py --fused data/fused --output /tmp/fused-check.json
```

Resultado local: 66 testes Python, 6 testes Node e 8 testes unittest aprovados;
integridade dos 3.687 registros fused sem problemas. Os oito unittest já estão
incluídos nos 66 testes Python, não são somados novamente.

Foi executado `web/tests/simulator.browser.cjs` com Playwright e Chromium local:
59 questões × respostas certa/errada × desktop/celular; 236 submissões verificadas,
12 imagens carregadas, prévia de 513 e bloqueio das 454 pendentes. Nenhuma exceção
JavaScript. O script aceita `ENEM_CHROMIUM` e `ENEM_CHROMIUM_ARGS` para o navegador
disponível no ambiente; não utiliza serviços externos nem chaves.

A prévia gerada não precisa ser versionada novamente: em checkout limpo a API
usa o snapshot imutável existente, aplicando os mesmos controles em tempo de
leitura. O publicador permite gerar a cópia idêntica para execução local.

Para regenerar imagens, opcionalmente:
`python scripts/publish_blue_candidates.py --restore-pdfs /diretorio/dos/pdfs`.
Esse comando exige que todos os hashes de provas, gabaritos e registros das 59
questões coincidam; nenhuma nova questão é aprovada pelo script.

Sem escrita em ArangoDB, alterações em credenciais, deploy ou serviços pagos.
O histórico de aquisição remota dos PDFs para 1.620 posições é uma auditoria
separada e continua sujeito às falhas de acesso/TLS documentadas no README.
