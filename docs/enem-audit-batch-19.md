# ENEM — lote 19: 35 questões com figura de 2022 e 2023

Catálogo: 1174 → **1209** pontuáveis. As 1174 anteriores permanecem byte a byte idênticas. Sexto lote da fase de figuras (grupo A), mesmo método dos lotes 14 a 18 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2022 D1 / D2 | 10 / 7 |
| 2023 D1 / D2 | 7 / 11 |

- **Verificação:** 35 recortes em 6 folhas de contato; os gates automáticos (nenhuma linha cortada, nenhum cabeçalho de outra questão, resposta do `ITENS_PROVA` = gabarito do PDF) não reprovaram nenhuma. As 35 recebem a, b, c oficiais (1200 questões com TRI).
- **Fora do lote:** 2023 D2 Q164 é oficialmente anulada (`ITENS_PROVA` com `X`); a checagem de identidade do construtor a barrou e ela saiu da seleção.
- **Correção no construtor:** o replay de 2023 D2 Q135 não reproduzia o PNG gerado pelo construtor. A causa era o cache de imagens do MuPDF: o construtor renderizava o primeiro pixmap antes de `store_shrink(100)`, enquanto o replay chama `store_shrink(100)` antes de cada render, e essa questão tem uma imagem de fundo com gradiente. O construtor agora chama `store_shrink(100)` antes de renderizar, e o replay bate byte a byte. (Os PNGs dos lotes 14 a 18 já reproduziam no replay.)

```sh
python scripts/build_enem_figure_batch_report.py --batch 19
python scripts/apply_enem_batch_19.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
