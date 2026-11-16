# ENEM — lote 34: 14 questões de idioma e de texto compartilhado (2017, 2018, 2024, 2025)

Catálogo: 1597 → **1611** pontuáveis. As 1597 anteriores permanecem byte a byte idênticas. Restam **9 posições**, todas anuladas oficiais (sem pontuação).

| Ano | Novas | Posições |
| --- | ---: | --- |
| 2017 | 5 | D1 Q1–5 (inglês) |
| 2018 | 2 | D1 Q4–5 (inglês) |
| 2024 | 1 | D1 Q4 (inglês) |
| 2025 | 6 | D1 Q6–11 |

- **Idioma (8):** só a versão em inglês conta na posição. A identidade vem do ITENS_PROVA oficial (`TP_LINGUA` 0, CO_PROVA já resolvido), com a letra igual à do gabarito oficial em inglês e a seção do caderno conferida pelo cabeçalho "Questões de 01 a 05 (opção inglês)" (`scripts/resolve_identity_idioma.py`). O idioma não é inferido do texto.
- **2024 D1 Q04:** estava no inventário como linha legada bloqueada (texto da Q05 em inglês, CO_ITEM 47987, sem gabarito). Com o ITENS_PROVA oficial a identidade fica resolvida (CO_ITEM 118157, gabarito A, que coincide com o gabarito oficial em inglês). O `apply_enem_batch_34.py` só substitui a linha legada se ela nunca pontuou e não foi publicada.
- **Banner da seção seguinte:** em 2017 Q5 e 2018 Q5 o recorte pegava o banner "LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS / Questões de 01 a 05 (opção espanhol)"; `BANNER_CUT` corta acima dele.
- **Texto compartilhado (2025 Q6–10):** "Texto para as Questões de 06 a 10" (página 6) entra como primeira região do recorte e no texto de apoio (`SHARED_PREFIX`); sem ele as questões não seriam respondíveis. A Q11 tem texto próprio.
- Todas foram vistas em folhas de contato: recortes completos, sem o texto de outra questão nem o da versão em espanhol.

```sh
python scripts/resolve_identity_idioma.py
python scripts/build_enem_figure_batch_report.py --batch 34
python scripts/apply_enem_batch_34.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) tirado da camada de texto; no texto compartilhado de 2025 o subtítulo itálico fica em dois parágrafos; descrição da imagem genérica; conferência por folha de contato. As versões em espanhol não são publicadas.
