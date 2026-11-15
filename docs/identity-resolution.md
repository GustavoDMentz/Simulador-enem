# Resolução de identidade (CO_ITEM) — 2018, 2019, 2020, 2023 e 2024 (D2)

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
| 2024 D2 CN / MT | 1419 / 1407 | 44/45, 45/45 |

As posições em que o CSV traz `X` e o PDF não traz letra são **anulações oficiais**: 2018 D2 Q163, 2020 D2 Q157, 2023 D2 Q164 e 2024 D2 Q129. Posições 1–5 de LC (idioma) não são resolvidas aqui. **2024 D1** ficou sem resolução porque o gabarito oficial do PDF não está no repositório. **2020 D2 digital** (35 itens publicados da aplicação digital) fica fora: o caderno resolvido é o regular.

## Resultado
- `data/audit/identity-resolution.json`: **755 itens** resolvidos em 18 de 19 combinações ano/dia/área tentadas.
- Dos 293 registros publicados nesses anos, **93 tinham CO_ITEM errado** (200 estavam certos, em geral por coincidência de posição entre cadernos).
- `web/published-questions.js` aplica o CO_ITEM resolvido antes da junção TRI e marca `identidade.status = VERIFIED`; se a resposta/área não bater, `CONFLICT` e **sem junção TRI**. Os bytes de `questions.jsonl` não mudam.
- Verificação independente: depois da correção, **0** das 71 linhas TRI juntadas tem resposta externa divergente do gabarito oficial.
- **2024 D2:** o CO_PROVA regular foi identificado (CN 1419, MT 1407), o que dá base objetiva para o conflito regular × reaplicação do PR #26.

## Ainda aberto
2024 D1 (falta o PDF do gabarito) e 2025 (o zip recusou conexão) continuam sem resolução; enquanto isso, o `co_item` e os parâmetros TRI desses anos não são confiáveis. 2021 e 2022 já eram consistentes (fused ≈ 99% do gabarito).
