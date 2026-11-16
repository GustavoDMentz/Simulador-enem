# ENEM — lote 32: 28 questões reavaliadas de 2017 a 2025

Catálogo: 1527 → **1555** pontuáveis. As 1527 anteriores permanecem byte a byte idênticas. Reavalia as posições que ficaram de fora nos lotes anteriores, agora com os gates e o recorte atuais (70 candidatas, sem as anuladas oficiais nem as de idioma).

| Ano | Novas |
| --- | ---: |
| 2017 | 3 |
| 2018 | 4 |
| 2019 | 7 |
| 2020 | 5 |
| 2022 | 2 |
| 2023 | 1 |
| 2025 | 6 |

- **Gates:** 28 aprovadas; 42 reprovaram e ficam para o próximo lote, por motivo: letras A–E fora de sequência na mesma coluna (alternativas em duas colunas ou formato incomum), tinta da linha anterior sobreposta ao cabeçalho, glifo privado no texto (corrigível por `TEXT_OVERRIDES`) e cabeçalho de outra questão dentro da região.
- **Regiões espúrias:** em 2025 D2 Q108, Q119, Q127, Q130 e 2022 D2 Q180 a "continuação" era a faixa de cabeçalho da página ("Exame Nacional do Ensino Médio") ou o logo da contracapa. `REGION_KEEP` mantém só a região real; conferido na imagem.
- Todas foram vistas em folhas de contato: recortes completos. 27 das 28 recebem a, b, c oficiais (1538 questões com TRI).

```sh
python scripts/build_enem_figure_batch_report.py --batch 32
python scripts/apply_enem_batch_32.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) com expoentes e índices achatados; descrição da imagem genérica; conferência por folha de contato.
