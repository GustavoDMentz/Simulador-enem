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


### Correção do transporte HTTPS no CI

A execução 40251131151 falhou: 0/18 PDFs, timeouts em download.inep.gov.br, sem publicação. O downloader forçava conexão direta e não acionava curl após timeout. Corrigido para respeitar o proxy do ambiente e tentar curl IPv4 verificado pelo ambiente e diretamente, mantendo CA personalizada, HTTPS e limites de tamanho/tempo. Uma indisponibilidade inicial de transporte é registrada e interrompe o lote; a verificação de completude continua falhando quando faltam fontes. Quatro regressões offline passaram com unittest. A conectividade externa depende da nova execução do GitHub; nenhum conteúdo de questão foi alterado.

## Diagnóstico HTTPS e independência dos workflows

Evidência reproduzida no GitHub Actions, commit `caf8b6a`:
[execução 40256859487](https://github.com/GustavoDMentz/Simulador-enem/actions/runs/40256859487).
Os logs e o artefato `enem-blue-official-audit` preservam comandos e resultados.
Nenhum parâmetro de verificação TLS foi relaxado; os testes OpenSSL apenas
inspecionam a negociação, sem baixar ou aceitar documentos.

- DNS observado: somente A `200.130.24.15`; IPv6 falhou em resolução (curl 6).
- HTTPS_PROXY, https_proxy, HTTP_PROXY, http_proxy e NO_PROXY estavam ausentes.
  Portanto, os ensaios “environment” e “direct” usaram efetivamente conexão direta;
  não foi possível comparar com um proxy real, pois nenhum estava configurado.
- SSL_CERT_FILE, SSL_CERT_DIR, CURL_CA_BUNDLE e REQUESTS_CA_BUNDLE ausentes.
  Python usou /usr/lib/ssl/cert.pem e /usr/lib/ssl/certs; curl/downloader receberam
  explicitamente /etc/ssl/certs/ca-certificates.crt. O contexto Python carregou
  121 certificados. Versões de curl/OpenSSL/Python e hash do bundle estão nos logs.
- curl IPv4 retornou 60 / verify=20 / http=000 com e sem --noproxy:
  “unable to get local issuer certificate”.
- OpenSSL IPv4, padrão e TLS 1.2, recebeu reset (errno 104), zero bytes de handshake,
  “no peer certificate available”. Seu “Verify return code: 0” NÃO demonstra
  confiança: não houve certificado nem handshake concluído.
- Não foi possível obter a cadeia apresentada por esse caminho. A evidência
  estabelece falha de transporte/confiança TLS, mas não identifica o emissor
  ausente nem permite atribuir definitivamente a causa ao servidor, à rede
  intermediária ou ao conjunto local de autoridades.

Não há correção de confiança demonstravelmente segura a aplicar com esses dados.
Não foram adicionadas CAs arbitrárias nem usados TLS sem verificação ou HTTP.
A página oficial gov.br oferece os links de origem, mas os PDFs descobertos
continuam hospedados no mesmo domínio bloqueado. Os PDFs previamente recuperados
do ZIP e vinculados aos hashes já atendem à restauração das 59 questões; não foram
tratados como uma nova aquisição remota bem-sucedida dos 18 PDFs.

### Separação mínima

O workflow `blue-official-audit.yml` é agora disparado explicitamente por
`workflow_dispatch`. Continua disponível, preserva diagnóstico e artefatos,
exige 18 PDFs e cobertura de 1.620 posições e termina com falha se faltarem fontes.
As execuções anteriores falhas continuam visíveis. Não há continue-on-error,
conversão de falha em sucesso ou aprovação adicional de questão.

A aquisição histórica nunca foi dependência do publicador nem dos endpoints:
ela escreve em `data/enem-pdfs` e `data/blue-staging`. A integração usa
`data/audit/manifest.json`, o snapshot restaurado, `data/blue-published` e as
imagens verificadas. Os testes existentes de publicação verificam exatamente
59 aprovações/513 prévias/454 pendências, hashes, nulidade de TRI e preservação
do conteúdo pendente. Os testes HTTP rejeitam conteúdo, identidade, respostas,
manifestos e arquivos gráficos inconsistentes.

Os workflows Python e integridade/API/ArangoDB continuam automáticos. Seus
gatilhos de PR agora incluem explicitamente manifestos, registros publicados e
imagens verificadas; os testes Node também são disparados por qualquer alteração
em web. Nenhum critério de aprovação foi reduzido.

### Verificação desta conclusão

Uma verificação local focal confirmou 59 identidades/conteúdos/imagens aprovados,
454 pendências sem pontuação e ausência de TRI. Dados, imagens e código de API
não foram modificados nesta etapa. Os testes de Chromium históricos não foram
repetidos porque não houve alteração de interface ou pontuação. Os checks remotos
da versão final devem ser consultados no PR; não se presume aprovação de execução
ainda pendente. Nenhum merge, deploy ou acesso ao banco de produção foi realizado.

A API do conector recusou a leitura da proteção clássica da main (403); a lista
pública de rulesets retornou vazia. Não foram alteradas regras administrativas.
A recomendação técnica de integração não substitui eventual regra administrativa
de revisão/check obrigatório que o conector não consegue consultar.
