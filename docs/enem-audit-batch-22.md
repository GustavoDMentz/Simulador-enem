# ENEM — lote 22: 11 questões que o extrator não lia (alternativas com letra separada por espaços)

Catálogo: 1272 → **1283** pontuáveis. As 1272 anteriores permanecem byte a byte idênticas. Mesmo método dos lotes 14 a 21 (recorte original; uma ou duas regiões empilhadas).

| Prova | Novas |
| --- | ---: |
| 2017 D1 (Q85, Q86, Q87) | 3 |
| 2020 D1 (Q36, Q67, Q68, Q69, Q70) | 5 |
| 2020 D2 (Q153, Q159, Q160) | 3 |

- **Causa:** essas questões estavam no "grupo B" (alternativas não lidas) porque o extrator só reconhecia alternativas no formato `A\t texto`. Em parte dos cadernos de 2017 e 2020 a letra vem seguida de dois ou mais espaços (`A  texto`). `scripts/extract_exam_candidates.py` agora cai nesse formato (`OPT2`) quando não acha nenhuma alternativa com tabulação; o restante do grupo B (61 questões) continua sem alternativas em texto, porque as alternativas são gráficas ou a questão tem fórmulas.
- **Verificação:** 11 recortes em folhas de contato (a 2020 D1 Q68 é de duas regiões, empilhadas sem corte); os gates não reprovaram nenhum. As 11 recebem a, b, c oficiais (1273 questões com TRI).
- **Fora deste lote:** as 61 do grupo B que seguem sem alternativas em texto (gráficas ou com fórmulas) e as de fronteira do lote 20 e 21.

```sh
python scripts/build_enem_figure_batch_report.py --batch 22
python scripts/apply_enem_batch_22.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio da camada do PDF, descrição da imagem genérica, conferência por folha de contato.
