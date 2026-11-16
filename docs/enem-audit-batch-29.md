# ENEM — lote 29: 32 questões de 2021 com linhas transcritas

Catálogo: 1477 → **1509** pontuáveis. Segunda frente de **2021**, com o mesmo método do [lote 28](enem-audit-batch-28.md): texto recuperado de outros cadernos pelo CO_ITEM e, nas linhas que continuam corrompidas em todos os cadernos, **transcrição manual conferida na imagem** (`data/audit/text-recovery-2021-fills.json`).

| Prova | Novas |
| --- | ---: |
| 2021 D1 | 17 |
| 2021 D2 | 15 |

- **Transcrições:** de 1 a 7 linhas por questão (4 a 7 na maioria; Q139 e Q166 ficaram com 1 e 2 depois da correção abaixo). Todas as 32 passaram nos gates e foram vistas em 6 folhas de contato: recortes completos.
- **TRI:** 31 das 32 recebem a, b, c oficiais (1494 questões com TRI).
- **Alternativas gráficas:** 2021 D2 Q179 (frações) usa o texto de apoio padrão; as linhas das barras de fração foram preenchidas só para fechar a lacuna.
- **Correções de texto** conferidas na imagem em 2021 D2 Q116, Q139, Q147 e Q179 (`TEXT_OVERRIDES`).

## Correção no lote 28
A detecção de lixo da camada de texto não cobria os controles C1 (`\x7f–\x9f`) nem símbolos soltos (`]$[`). Com a regra ampliada, o único registro publicado afetado foi **2021 D2 Q164**: os algarismos romanos "I" e "II" da tabela estavam como `\x82` no texto de apoio. Agora vêm do caderno rosa. O lote 28 foi regenerado e só esse registro mudou (recorte e gabarito idênticos). O gate do construtor (`STRANGE`) também passou a barrar esses caracteres.

## Faltam em 2021
19 posições: mais de 7 linhas corrompidas ou sem texto aproveitável (Q15, Q16, Q20, Q25, Q30, Q34, Q42, Q45; D2 Q94, Q110, Q111, Q118, Q120, Q134, Q138, Q156, Q157, Q161, Q175).

```sh
python scripts/recover_2021_text.py --itens ITENS_PROVA_2021.csv --pdf-dir DIR_DOS_CADERNOS --out data/audit/text-recovery-2021.json
python scripts/build_enem_figure_batch_report.py --batch 29
python scripts/apply_enem_batch_29.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) com linhas transcritas à mão e justificações largas que fragmentam algumas linhas; descrição da imagem genérica; conferência por folha de contato.
