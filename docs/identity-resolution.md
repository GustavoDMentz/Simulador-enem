# Resolução de identidade (CO_ITEM) — 2018, 2019, 2020 e 2023–2025

## Problema
O ITENS_PROVA oficial traz **vários CO_PROVA azuis por área** (regular, reaplicação, PPL…). O `fuse.py` escolheu, em alguns anos, um CO_PROVA azul que **não é o caderno do PDF que auditamos**. Sintomas:

- o `gabarito_oficial` do fused diverge do gabarito oficial em cerca de metade das posições (2018, 2019, 2020, 2023, 2024, 2025);
- 150 conflitos de resposta na junção TRI (`data/tri/external-staging/audit-2018-2025.md`);
- o `co_item` publicado (usado só para juntar parâmetros TRI) aponta, nessas posições, para outro item.

## Método (`scripts/resolve_identity.py`)
1. `scripts/fetch_inep_itens_prova.py` baixa **só** o ITENS_PROVA de `microdados_enem_ANO.zip` (HTTP range; ~15 e ~56 KB comprimidos; zip inteiro não baixado; CRC32 conferido). Ficam em `data/audit/identity/` apenas as linhas AZUL e colunas de identidade, com URL e SHA-256 do CSV bruto em `sources.json`.
2. Para cada (ano, dia, área), compara a sequência de respostas de cada CO_PROVA azul com o **gabarito oficial do PDF**. O caderno certo é o único com ≥ 97% de concordância (os demais ficam ≤ 60%).
3. Posição → CO_ITEM só é aceita para o CO_PROVA escolhido.

| Prova | CO_PROVA escolhido | Concordância |
| --- | --- | --- |
| 2018 D1 LC / CH · D2 CN / MT | 455 / 451 · 447 / 459 | 40/40, 45/45 · 45/45, 44/45 |
| 2019 D1 LC / CH · D2 CN / MT | 511 / 507 · 503 / 515 | 40/40, 45/45 · 45/45, 45/45 |
| 2020 D1 LC / CH · D2 CN / MT | 577 / 567 · 597 / 587 | 40/40, 45/45 · 44/44, 43/43 |
| 2023 D1 LC / CH · D2 CN / MT | 1201 / 1191 · 1221 / 1211 | 40/40, 45/45 · 45/45, 44/45 |
| 2024 D1 LC / CH · D2 CN / MT | 1395 / 1383 · 1419 / 1407 | 40/40, 45/45 · 44/44, 45/45 |
| 2025 D1 LC / CH · D2 CN / MT | 1459 / 1447 · 1483 / 1471 | 40/40, 45/45 · 43/43, 44/44 |

A comparação ignora posições anuladas (PDF sem letra ou "Anulado", CSV `X`) e as posições 1–5 de LC (idioma); por isso 2018 D2 MT passou de 44/45 para 44/44.

As posições em que o CSV traz `X` e o PDF não traz letra são **anulações oficiais**: 2018 D2 Q163, 2020 D2 Q157, 2023 D2 Q164, 2024 D2 Q129 e 2025 D2 Q123, Q132 e Q174. Posições 1–5 de LC (idioma) não são resolvidas aqui. O gabarito oficial de 2024 D1 foi baixado de `download.inep.gov.br` (SHA-256 em `data/audit/identity/sources.json`). **2020 D2 digital** (35 itens publicados da aplicação digital) fica fora: o caderno resolvido é o regular.

## Resultado
- `data/audit/identity-resolution.json`: **1015 itens** resolvidos em **24 de 24** combinações ano/dia/área.
- Dos 438 registros publicados nesses anos, **157 tinham CO_ITEM errado** (281 estavam certos, em geral por coincidência de posição entre cadernos).
- `web/published-questions.js` aplica o CO_ITEM resolvido antes da junção TRI e marca `identidade.status = VERIFIED`; se a resposta/área não bater, `CONFLICT` e **sem junção TRI**. Os bytes de `questions.jsonl` não mudam.
- Verificação independente: depois da correção, **0** das 134 linhas TRI juntadas tem resposta externa divergente do gabarito oficial.
- **2024 D2:** o CO_PROVA regular foi identificado (CN 1419, MT 1407), base objetiva para o conflito regular × reaplicação do PR #26.

## Ainda aberto
2021 e 2022 já eram consistentes (fused ≈ 99% do gabarito) e não foram incluídas; o ITENS_PROVA delas daria a prova formal. Os 35 itens de 2020 D2 da aplicação digital precisam do ITENS_PROVA/gabarito digital.
