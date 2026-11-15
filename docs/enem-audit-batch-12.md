# ENEM — lote 12: 107 questões de 2017, 2022 e 2024 D2

Catálogo: 796 → **903** pontuáveis. As 796 anteriores permanecem byte a byte idênticas (`previous_lines_sha256`).

| Prova | Novas |
| --- | ---: |
| 2017 D1 / D2 | 36 / 16 |
| 2022 D1 / D2 | 49 / 0 |
| 2024 D1 / D2 | 0 / 6 |

Mesmo método do lote 11: texto da camada de texto do PDF oficial, `co_item`/`co_habilidade`/`in_item_aban` da resolução de identidade (ITENS_PROVA oficial), resposta do ITENS_PROVA igual ao gabarito do PDF, conferência visual de cada região em folhas de contato e reaplicação contra os PDFs originais com SHA-256.

```sh
python scripts/build_enem_batch_12_report.py
python scripts/apply_enem_batch_12.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Seleção
Todas as candidatas `tier_a` de região única ainda fora do manifesto nessas provas (107). 2022 D2 e 2024 D1 não tinham candidata nova de texto puro; as demais são `tier_b` (figuras, quebras de linha etc.) e ficam fora. Em 2024 D2 as barras azuis do cabeçalho são ornamento, não figura.

## Limites
Conferência visual por região, não pixel a pixel. Parâmetros TRI `null`; o carregador junta TRI pelo CO_ITEM resolvido.
