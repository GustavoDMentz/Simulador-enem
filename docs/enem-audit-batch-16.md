# ENEM — lote 16: 47 questões com figura de 2019

Catálogo: 1054 → **1101** pontuáveis. As 1054 anteriores permanecem byte a byte idênticas. Terceiro lote da fase de figuras (grupo A), mesmo método dos lotes 14 e 15 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2019 D1 | 24 |
| 2019 D2 | 23 |

- **Verificação:** 47 recortes em 8 folhas de contato; os gates automáticos (nenhuma linha cortada, nenhum cabeçalho de outra questão, resposta do `ITENS_PROVA` = gabarito do PDF) não reprovaram nenhuma, e o construtor não achou glifos privados no texto.
- **Ajuste do recorte:** nas páginas de 2019 a aba escura da margem é preenchida e sai da página; o construtor passou a ignorar preenchimentos que ultrapassam os limites da página, e as folhas foram refeitas.
- **TRI:** 46 das 47 recebem a, b, c oficiais (1092 questões com TRI). 2019 D2 Q122 não tem parâmetros no `ITENS_PROVA` do Inep (item sem parâmetros), então segue sem TRI.

```sh
python scripts/build_enem_figure_batch_report.py --batch 16
python scripts/apply_enem_batch_16.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
