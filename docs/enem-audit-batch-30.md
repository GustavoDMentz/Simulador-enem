# ENEM — lote 30: 8 questões de 2021 com muitas linhas transcritas

Catálogo: 1509 → **1517** pontuáveis. Terceira frente de **2021** ([lote 28](enem-audit-batch-28.md) e [lote 29](enem-audit-batch-29.md)): texto de outros cadernos pelo CO_ITEM mais transcrição manual das linhas corrompidas em todos os cadernos (`data/audit/text-recovery-2021-fills.json`), aqui com 8 a 12 linhas por questão.

| Prova | Novas |
| --- | ---: |
| 2021 D1 | 3 (Q16, Q20, Q30) |
| 2021 D2 | 5 (Q94, Q110, Q111, Q134, Q175) |

- Todas passaram nos gates; as 8 foram vistas em folha de contato, recortes completos. Em linhas com justificação larga (Q110 e Q175) cada palavra vem como uma linha própria na camada de texto; a transcrição segue essa fragmentação, e a leitura das palavras unidas dá o texto.
- **TRI:** 8 das 8 recebem a, b, c oficiais (1502 questões com TRI).

## Faltam em 2021 (11 posições)
D1 Q15, Q25, Q34, Q42, Q45; D2 Q118, Q120, Q138, Q156, Q157, Q161. Têm de 12 a 80 linhas corrompidas (praticamente a questão inteira): exigem transcrição completa. A Q161 tem ainda cabeçalho duplicado no azul.

```sh
python scripts/build_enem_figure_batch_report.py --batch 30
python scripts/apply_enem_batch_30.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) transcrito à mão; descrição da imagem genérica; conferência por folha de contato.
