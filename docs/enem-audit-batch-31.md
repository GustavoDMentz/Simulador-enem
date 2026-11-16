# ENEM — lote 31: 10 questões de 2021 (transcrição individual, 2021 completo)

Catálogo: 1517 → **1527** pontuáveis. Fecha a frente de **2021**: com este lote, **179 das 180 posições** estão no banco; a que falta é a **D2 Q138**, oficialmente anulada (o gabarito do PDF não coincide com o ITENS_PROVA e o gate de identidade a barra).

Cada uma das 10 foi transcrita e conferida individualmente na imagem (`data/audit/text-recovery-2021-fills.json`).

| Prova | Novas |
| --- | ---: |
| 2021 D1 | 5 (Q15, Q25, Q34, Q42, Q45) |
| 2021 D2 | 5 (Q118, Q120, Q156, Q157, Q161) |

## O que mudou no método
- **Regiões espúrias:** em D1 Q45 a "continuação" detectada era a página das instruções da redação; em D2 Q118, Q120 e Q161 era a página inteira repetida. `REGION_KEEP` em `scripts/extract_exam_candidates.py` mantém só a região que pertence à questão (conferido na imagem). Com a região certa, os outros cadernos passaram a casar e as lacunas caíram (Q45: 80 → 9; Q118: 23 → 5; Q161: 12 → 6).
- **Ponto final lido como "4":** linhas do azul terminadas em letra + `4` (ex.: "narrador4") passam a ser tratadas como corrompidas. Nenhum registro já publicado tinha esse defeito (varredura nos 2021 publicados).
- **Alternativas gráficas em duas colunas** (D2 Q161): `GRAPHIC_STEM` monta o enunciado e usa o texto de apoio padrão para as alternativas.
- **Preenchimento de linha inteira:** `!texto` substitui a linha (rótulo "A =" da matriz da D2 Q157, que parecia a letra de uma alternativa).
- Rótulos de figura (D2 Q156 e Q157): a camada de texto os traz fora da ordem de leitura; os preenchimentos só fecham as lacunas, não aparecem na tela (o enunciado vem de `TEXT_OVERRIDES`) e a ordem é aproximada.
- **TRI:** 9 das 10 recebem a, b, c oficiais (1511 questões com TRI).

```sh
python scripts/recover_2021_text.py --itens ITENS_PROVA_2021.csv --pdf-dir DIR_DOS_CADERNOS --out data/audit/text-recovery-2021.json
python scripts/build_enem_figure_batch_report.py --batch 31
python scripts/apply_enem_batch_31.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio transcrito à mão (comando e base ocultos na tela, lidos por leitores de tela); rótulos de figura em ordem aproximada; descrição da imagem genérica; conferência por folha de contato.
