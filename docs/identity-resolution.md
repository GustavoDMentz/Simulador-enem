# Resolução de identidade (CO_ITEM) — 2018 e 2023

## Problema
O ITENS_PROVA oficial traz **vários CO_PROVA azuis por área** (regular, reaplicação, PPL…). O `fuse.py` escolheu, em alguns anos, um CO_PROVA azul que **não é o caderno do PDF que auditamos**. Sintomas:

- o `gabarito_oficial` do fused diverge do gabarito oficial em cerca de metade das posições (2018, 2019, 2020, 2023, 2025);
- 150 conflitos de resposta na junção TRI (`data/tri/external-staging/audit-2018-2025.md`);
- o `co_item` publicado (usado só para juntar parâmetros TRI) aponta, nessas posições, para outro item.

## Método (`scripts/resolve_identity.py`)
1. `scripts/fetch_inep_itens_prova.py` baixa **só** o ITENS_PROVA de `microdados_enem_ANO.zip` (HTTP range; ~15 e ~56 KB comprimidos; zip inteiro não baixado; CRC32 conferido). Ficam em `data/audit/identity/` apenas as linhas AZUL e colunas de identidade, com URL e SHA-256 do CSV bruto em `sources.json`.
2. Para cada (ano, dia, área), compara a sequência de respostas de cada CO_PROVA azul com o **gabarito oficial do PDF**. O caderno certo é o único com ≥ 97% de concordância (os demais ficam ≤ 60%).
3. Posição → CO_ITEM só é aceita para o CO_PROVA escolhido.

| Prova | CO_PROVA escolhido | Concordância |
| --- | --- | --- |
| 2018 D1 LC / CH | 455 / 451 | 40/40 / 45/45 |
| 2018 D2 CN / MT | 447 / 459 | 45/45 / 44/45 |
| 2023 D1 LC / CH | 1201 / 1191 | 40/40 / 45/45 |
| 2023 D2 CN / MT | 1221 / 1211 | 45/45 / 44/45 |

Os dois itens de MT que divergem são **anulações oficiais** (PDF "Anulado", CSV "X"): 2018 D2 Q163 e 2023 D2 Q164. Posições 1–5 de LC (idioma) não são resolvidas aqui.

## Resultado
- `data/audit/identity-resolution.json`: 350 itens resolvidos.
- Dos 92 registros publicados de 2018/2023, **39 tinham CO_ITEM errado** (53 estavam certos, em geral por coincidência de posição entre cadernos).
- `web/published-questions.js` aplica o CO_ITEM resolvido antes da junção TRI e marca `identidade.status = VERIFIED`; se a resposta/área não bater, `CONFLICT` e **sem junção TRI**. Os bytes de `questions.jsonl` não mudam.
- Verificação independente: depois da correção, **0** das linhas TRI juntadas tem resposta externa divergente do gabarito oficial (antes, 150 conflitos no catálogo).

## Ainda aberto
2019, 2020, 2024 e 2025 mostram o mesmo sintoma (fused × gabarito ≈ 40–55%) e precisam do mesmo cruzamento. O zip de 2025 recusou conexão. Enquanto não resolvidos, o `co_item` e os parâmetros TRI desses anos não são confiáveis.
