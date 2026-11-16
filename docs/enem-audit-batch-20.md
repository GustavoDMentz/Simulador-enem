# ENEM — lote 20: 9 questões com figura de 2020 (sobras do grupo A)

Catálogo: 1209 → **1218** pontuáveis. As 1209 anteriores permanecem byte a byte idênticas. Fecha a fase 1 (grupo A: região única, figura, cinco alternativas em texto), mesmo método dos lotes 14 a 19 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2020 D1 (Q07, Q15, Q30, Q33, Q44, Q51, Q65, Q88) | 8 |
| 2020 D2 (Q158) | 1 |

- **Verificação:** 9 recortes conferidos em folhas de contato; os gates automáticos não reprovaram nenhum. As 9 recebem a, b, c oficiais (1209 questões com TRI).
- **Fora do lote (4):** 2020 D1 Q14, Q22, Q25 e Q26. Nessas, a última linha da questão anterior fica colada ao cabeçalho "Questão n" (as caixas das linhas se sobrepõem em alguns pontos), então o recorte traz um pedaço do fim da questão anterior; o gate reprovou Q14, Q25 e Q26, e a Q22 foi pega na conferência visual. É o mesmo problema de fronteira que já tinha deixado de fora 2020 D1 Q06, Q48 e Q49 no lote 11. Ficam para um tratamento de fronteira dedicado (cortar exatamente no cabeçalho sem deixar fragmentos).
- **Também fora do grupo A:** 2023 D2 Q164 e 2024 D2 Q129, oficialmente anuladas.

```sh
python scripts/build_enem_figure_batch_report.py --batch 20
python scripts/apply_enem_batch_20.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
