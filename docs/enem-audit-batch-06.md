# ENEM — Lote 06

Base: `705e060d24bc27507049499ec687830e31092d6e`, após PR #7. Branch: `feat/enem-audit-batch-06`.

## Resultado

- Inventário: 513 questões.
- Anteriores: 238 publicadas, preservadas integralmente, inclusive gabaritos.
- Selecionadas e comparadas com a prova e o gabarito: **50**.
- Novas aprovações: **50**; rejeitadas ou mantidas em revisão dentro da seleção: **0**.
- Total: **288 publicadas**, **225 pendentes bloqueadas**.
- Nenhum parâmetro TRI atribuído; nenhum acesso a banco de produção.

## Seleção e identificadores

Caderno azul 1, aplicação regular, primeiro dia de 2024. A concentração em uma fonte recuperável reduziu o custo de aquisição e permitiu comparar integralmente páginas e continuidade. Não houve nova auditoria dos itens anteriores.

Linguagens: `2024_AZUL_D1_Q06`, `Q07`, `Q08`, `Q09`, `Q10` (mesmo prefixo).

Humanas: `2024_AZUL_D1_Q46` a `2024_AZUL_D1_Q90`, inclusive. Os 50 identificadores completos estão em `data/audit/batch-06-review.json`, campo `results[].id`.

A seleção contém 47 questões textuais e três apoios visuais verificáveis (Q53, Q77, Q86). A completude do JSON não foi usada como certificado. As páginas oficiais 5–6 e 20–31 foram renderizadas e inspecionadas; Q07 foi conferida através da mudança de coluna, e Q77–Q79 respeitam a largura integral da página 28.

## Fontes e evidências

- [Prova oficial](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D1_CD1.pdf), SHA-256 `b0adc1dc79a002aba36f725f1ef792cf53e47ff75ee012638ef34a4e6fbb18f5`.
- [Gabarito oficial](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D1_CD1.pdf), SHA-256 `673d3d060156d6ad610ecf96c3dd0b8c61f361e16c57860c4ca5b5fecc8be050`.

As primeiras tentativas HTTPS falharam com 502/503; os arquivos foram recuperados pela rota HTTP do mesmo host oficial. O gabarito impresso foi inspecionado visualmente e comparado à extração do parser existente. Os PDFs de trabalho não são novas dependências de execução do simulador.

Cada decisão registra antes/depois, campos alterados, texto extraído, hash desse texto, página e coordenadas, hash do registro, gabarito e fontes. Os três PNGs incluem todos os elementos visuais e créditos do apoio, sem o comando e sem as alternativas. Seus hashes e coordenadas também estão no relatório e no manifesto de publicação.

## Correções demonstráveis

- Q06/Q07: título do texto separado do comando real; Q07 conserva as três minibiografias e a continuidade entre colunas.
- Q06-C: “revenciam” → “reverenciam”; Q08-C: “cordofones” → “cordófonos”.
- Q09/Q10: recuperação da prosa original e separação do comando; corrigidos erros como “Depressão, depressão”, “programão”, “trombos” e “PHL”.
- Q47-B: “oposição à eugenia” → “imposição eugênica”.
- Q49-A/B: “expansão estratégica” e “ascensão gradual”, conforme a prova.
- Q50: contraste entre o homem “odiado” e o mais “amado” restaurado; Q51-D: “concessões” → “compassos”.
- Q60-C: “delineados” → “delimitados”; Q61: “premissa” → “problema”; Q66-E: “enfraquecimento” → “enrijecimento”; Q68-A: “ventos frios” → “ventos alísios”.
- Outros créditos, acentos, pontuação e segmentação foram recuperados diretamente da prova. O relatório contém as diferenças completas, incluindo capitalização das alternativas.

## Apresentação

Os 47 textos usam HTML sem imagem repetida. Foram normalizados apenas espaços e quebras tipográficas, com os rótulos TEXTO I/II/III preservados; `km²`, percentuais e graus permanecem textuais e exatos.

Q53 preserva o gráfico com os dois traçados e eixos; Q77 mantém as três capas e sua composição; Q86 mantém os dois mapas, datas, legendas, escalas, orientação e créditos. Esses apoios usam o comportamento de composição ampliável do PR #7, sem repetir seu conteúdo em HTML. Descrições contextuais não substituem os originais nem inventam dados numéricos.

## Reprodução

Obtenha os dois PDFs oficiais acima como `2024-d1.pdf` e `2024-key.pdf` no diretório escolhido. O aplicador exige os hashes exatos, verifica cada palavra e alternativa contra a extração das regiões já revisadas e reproduz os PNGs:

```sh
python scripts/apply_enem_batch_06.py --pdf-root data/sources/batch06
python scripts/publish_blue_candidates.py
python scripts/build_question_presentation.py --check
python -m pytest -q tests scripts/tests
node --test web/tests/*.test.js
python scripts/audit_fused_db.py --fused data/fused --output /tmp/b06-integrity.json
```

O aplicador reproduz decisões fixas e explícitas; não seleciona nem aprova questões por heurística. A reaplicação é idempotente. Não modifica o snapshot de recuperação, os dados fused ou o banco.

## Validação e limitações

Os testes verificam a preservação byte a byte das 238 questões anteriores, os 50 novos vínculos de evidência, hashes, ausência de TRI e a política fail-closed. O catálogo anterior reconstruído conserva SHA-256 `8351f7ef5c3508e9bc1277d7ad8fb6bd6d82113b897fd31db1c621dfdcc906d3`.

`web/tests/batch06.browser.cjs` percorre as 50 novas questões em desktop e celular, confere texto/A–E, respostas corretas/incorretas, apoios, ampliação por teclado, Escape, foco, aleatoriedade e exclusão das pendentes. `web/tests/rendering.browser.cjs` repete os cinco casos do PR #7. [Capturas da amostra](batch06-screenshots/) incluem texto, continuidade, gráfico, capas e mapas.

A seleção concentra-se em LC/CH; CN/MT não foram forçadas para diversificar o lote. As três composições visuais têm descrições contextuais, sem transcrição integral dos mapas ou reconstrução numérica do gráfico. As 225 pendentes não foram certificadas. O arquivo `enem-parte-00` estava indisponível; não foi utilizado como fonte.

Resultados finais: **77 testes Python**, **9 Node/API**, integridade dos **3.687 registros** sem problemas e reaplicação idempotente. Chromium: **50 novas questões em cada viewport**, **200 respostas corrigidas**, **20 seleções aleatórias**, três apoios ampliáveis e **225 pendentes bloqueadas**; sem erros JavaScript ou transbordamento. Os cinco casos anteriores de renderização também passaram em desktop e celular. Resultados estruturados em `data/audit/batch-06-verification.json`; 10 capturas finais da amostra foram inspecionadas.
