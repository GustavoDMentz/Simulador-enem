# ENEM — lote 18: 41 questões com figura de 2025

Catálogo: 1133 → **1174** pontuáveis. As 1133 anteriores permanecem byte a byte idênticas. Quinto lote da fase de figuras (grupo A), mesmo método dos lotes 14 a 17 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2025 D1 | 19 |
| 2025 D2 | 22 |

- **Verificação:** 41 recortes em 7 folhas de contato; os gates automáticos (nenhuma linha cortada, nenhum cabeçalho de outra questão, resposta do `ITENS_PROVA` = gabarito do PDF) não reprovaram nenhuma, e o construtor não achou glifos privados no texto. As 41 recebem a, b, c oficiais (1165 questões com TRI).
- Nenhum ajuste novo no construtor foi necessário para 2025.

```sh
python scripts/build_enem_figure_batch_report.py --batch 18
python scripts/apply_enem_batch_18.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
