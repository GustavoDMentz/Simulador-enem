# ENEM — lote 17: 32 questões com figura de 2024

Catálogo: 1101 → **1133** pontuáveis. As 1101 anteriores permanecem byte a byte idênticas. Quarto lote da fase de figuras (grupo A), mesmo método dos lotes 14 a 16 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2024 D1 | 1 |
| 2024 D2 | 31 |

- **Verificação:** 32 recortes em 6 folhas de contato; os gates automáticos (nenhuma linha cortada, nenhum cabeçalho de outra questão, resposta do `ITENS_PROVA` = gabarito do PDF) não reprovaram nenhuma. As 32 recebem a, b, c oficiais (1124 questões com TRI).
- **Fora do lote:** 2024 D2 Q129 saiu da seleção porque é oficialmente anulada (`ITENS_PROVA` com `X`, gabarito do PDF "Anulado"); a checagem de identidade do construtor a barrou.
- **Ajustes do recorte:** as páginas de 2024 têm uma faixa decorativa de ondas na margem (imagem estreita que sai da página, mais desenhos dentro dos 24 pt da borda). O construtor agora ignora imagens estreitas na margem e desenhos dentro da faixa, e deixou de somar blocos de imagem do texto bruto; as folhas foram refeitas antes da conferência. O inventário de PDFs não traz as fontes de 2024 D1, então o construtor usa a URL e os SHA-256 já auditados no manifesto de publicação (os arquivos continuam sendo conferidos por SHA-256).

```sh
python scripts/build_enem_figure_batch_report.py --batch 17
python scripts/apply_enem_batch_17.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
