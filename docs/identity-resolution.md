# Resolução de identidade (CO_ITEM) — 2017 a 2025

## Problema
O ITENS_PROVA oficial traz **vários CO_PROVA azuis por área** (regular, reaplicação, PPL…). O `fuse.py` escolheu, em alguns anos, um CO_PROVA azul que **não é o caderno do PDF que auditamos**. Sintomas:

- o `gabarito_oficial` do fused diverge do gabarito oficial em cerca de metade das posições (2018, 2019, 2020, 2023, 2024, 2025);
- 150 conflitos de resposta na junção TRI com uma base externa não oficial (já removida do repositório; ver `docs/tri-oficial.md`);
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
| 2017 D1 LC / CH · D2 CN / MT | 399 / 395 · 391 / 403 | 40/40, 45/45 · 45/45, 45/45 |
| 2021 D1 LC / CH · D2 CN / MT | 889 / 999 · 909 / 899 | 40/40, 45/45 · 45/45, 44/44 |
| 2022 D1 LC / CH · D2 CN / MT | 1179 / 1175 · 1187 / 1183 | 40/40, 45/45 · 45/45, 44/44 |

Em 2021 e 2022 há **dois CO_PROVA azuis com o mesmo gabarito** (regular e reaplicação trazem os mesmos itens); a resolução só é aceita porque os dois mapeiam posição → CO_ITEM de forma idêntica (`equivalent_co_prova` no JSON). Em 2017 as posições do CSV são relativas à área (CH 1–45, CN 1–45, MT 1–45) e, em LC, as questões comuns começam na 11 (1–5 inglês, 6–10 espanhol); o resolvedor converte tudo para a posição global 1–180.

A comparação ignora posições anuladas (PDF sem letra ou "Anulado", CSV `X`) e as posições 1–5 de LC (idioma); por isso 2018 D2 MT passou de 44/45 para 44/44.

As posições em que o CSV traz `X` e o PDF não traz letra são **anulações oficiais**: 2018 D2 Q163, 2020 D2 Q157, 2023 D2 Q164, 2024 D2 Q129 e 2025 D2 Q123, Q132 e Q174, 2021 D2 Q138 e 2022 D2 Q157. Posições 1–5 de LC (idioma) são resolvidas à parte, por `scripts/resolve_identity_idioma.py` (abaixo). O gabarito oficial de 2024 D1 foi baixado de `download.inep.gov.br` (SHA-256 em `data/audit/identity/sources.json`). **2020 D2 digital** (35 itens publicados da aplicação digital) fica fora: o caderno resolvido é o regular.

## Resultado
- `data/audit/identity-resolution.json`: **1540 itens** resolvidos em **36 de 36** combinações ano/dia/área (2017–2025).
- Dos 724 registros publicados nesses anos, **160 tinham CO_ITEM errado** (564 estavam certos, em geral por coincidência de posição entre cadernos).
- `web/published-questions.js` aplica o CO_ITEM resolvido antes da junção TRI e marca `identidade.status = VERIFIED`; se a resposta/área não bater, `CONFLICT` e **sem junção TRI**. Os bytes de `questions.jsonl` não mudam.
- Verificação independente: depois da correção, **0** das 285 linhas TRI juntadas tem resposta externa divergente do gabarito oficial.

## Idioma (posições 1–5 de LC)
As 37 questões de idioma já publicadas (todas em inglês, 2018–2025) são resolvidas por `scripts/resolve_identity_idioma.py`, que acrescenta os itens (com `lingua`) a `identity-resolution.json`. O ITENS_PROVA traz duas linhas por posição (`TP_LINGUA` 0 = inglês, 1 = espanhol; confirmado pelo gabarito oficial, em que as letras de inglês e espanhol diferem nas posições 3 a 5 de 2018). O idioma **não é inferido do texto**: vem do manifesto (região do PDF oficial conferida no lote 08) e é conferido pela seção do caderno ("Questões de 01 a 05 (opção inglês|espanhol)"). Só é aceito quando concordam a seção, a variante de idioma do ITENS_PROVA, a letra do gabarito oficial desse idioma e o gabarito publicado. Resultado: 37 de 37 resolvidas, e 24 tinham `co_item` errado no catálogo (o `co_item` de outra variante ou de outro caderno).

O lote 34 acrescenta as **8 posições em inglês que ainda não estavam no catálogo** (2017 Q1–5, 2018 Q4–5 e 2024 Q4), com a mesma regra: região = primeiro cabeçalho "Questão n" (seção em inglês, conferida pelo cabeçalho "Questões de 01 a 05 (opção inglês)"), linha do ITENS_PROVA com `TP_LINGUA` 0 no CO_PROVA escolhido e letra igual à do gabarito oficial em inglês (`unpublished_english` em `language_resolution`). A 2024 D1 Q04, antes bloqueada por conflito de identidade, fica resolvida: CO_ITEM 118157, gabarito A; a linha legada (texto da Q05 e CO_ITEM 47987, sem pontuação) foi substituída no inventário.

## 2020 D2 — aplicação digital
As 35 questões publicadas da aplicação digital (`application: digital` no manifesto) são resolvidas por `scripts/resolve_identity_digital.py`, que usa o gabarito oficial digital (`2020_GB_digital_D2_CD7.pdf`, SHA-256 conferido com o manifesto). Entre os CO_PROVA azuis de CN e de MT, só um de cada área tem a sequência de respostas igual à do gabarito digital: **699** (CN, 45/45) e **695** (MT, 44/44); os outros ficam em 9–12 acertos. Cada questão só entra quando a resposta do ITENS_PROVA, a letra do gabarito digital e o gabarito publicado coincidem: 35 de 35, e 19 tinham `co_item` errado no catálogo (vinham do caderno regular). Os itens ganham `aplicacao: digital` em `identity-resolution.json`; `skipped_other_application` continua listando-os como não pertencentes ao caderno regular.

## Ainda aberto
As versões em espanhol não entram no catálogo: cada posição de idioma vale uma questão e adotamos a versão em inglês (a mesma já usada nas demais).
