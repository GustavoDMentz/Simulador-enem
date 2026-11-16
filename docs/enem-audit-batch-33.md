# ENEM — lote 33: 42 questões reavaliadas de 2017 a 2025

Catálogo: 1555 → **1597** pontuáveis. As 1555 anteriores permanecem byte a byte idênticas. Fecha as 42 candidatas que reprovaram nos gates do lote 32 (sem as anuladas oficiais nem as de idioma).

| Ano | Novas |
| --- | ---: |
| 2017 | 3 |
| 2018 | 3 |
| 2019 | 1 |
| 2020 | 3 |
| 2022 | 11 |
| 2023 | 2 |
| 2024 | 11 |
| 2025 | 8 |

- **Marca-d'água:** o gate de "tinta da linha anterior" tratava a marca-d'água diagonal ("ENEM 2022 ENEM 2022…", corpo 1,8) como tinta da questão de cima; ela agora é ignorada (11 questões).
- **Regiões duplicadas:** em questões que ocupam a página inteira a "continuação" era a mesma página relida (2017 D2 Q121 e Q152; 2018 D2 Q159 e Q173; 2019 D2 Q139; 2022 D2 Q95 e Q156; 2023 D2 Q132; 2024 D2 Q161 e Q168; 2025 D2 Q138 e Q169); `REGION_KEEP` mantém só a região real. Em 2018 D2 Q126 a página repete a questão vizinha; em 2020 D1 Q58 a faixa do topo é resto da vizinha; em 2024 D2 Q180 a continuação é o logo "enem" da contracapa.
- **Continuação de 2025 D1 (Q16, Q44, Q50, Q67):** a faixa de largura total trazia o fim da questão vizinha; `CONT_X0` limita a região à coluna direita. Em 2025 D2 Q135 as alternativas ficam na coluna direita (`EXTRA_REGION`).
- **Letras com espaço:** em 2020 D1 Q38 e Q57 as letras A–E vêm com espaços em vez de tabulação (`SPACE_OPT`).
- **Conteúdo transcrito (`FULL_OVERRIDES`):** onde a camada de texto tem glifos privados de fórmulas ou as letras das alternativas gráficas não saem como texto, o enunciado, o texto-base e as alternativas foram transcritos da imagem do recorte (e do texto do PDF) e conferidos: 2017 D2 Q121, Q136, Q152; 2018 D2 Q159, Q173; 2019 D2 Q139; 2020 D1 Q58; 2022 D2 Q95, Q103, Q108, Q115, Q116, Q156; 2023 D2 Q132, Q170; 2024 D2 Q127, Q148, Q161, Q168, Q174; 2025 D2 Q135, Q138, Q160, Q169. Na 2022 D1 Q12 o marcador de travessão de diálogo é removido do texto.
- Todas foram vistas em folhas de contato: recortes completos. As 42 recebem a, b, c oficiais (1580 questões com TRI).

```sh
python scripts/build_enem_figure_batch_report.py --batch 33
python scripts/apply_enem_batch_33.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) transcrito à mão nas fórmulas e nas alternativas gráficas, sem formatação de expoentes e frações; descrição da imagem genérica; conferência por folha de contato.
