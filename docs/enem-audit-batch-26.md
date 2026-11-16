# ENEM — lote 26: 49 questões com fórmulas de 2019, 2020, 2022 e 2023

Catálogo: 1361 → **1410** pontuáveis. As 1361 anteriores permanecem byte a byte idênticas. Segundo lote das questões separadas só por conterem expoentes, índices ou fórmulas (`sobrescrito_ou_indice`), mesmo método do lote 25 (`docs/enem-audit-batch-25.md`).

| Prova | Novas |
| --- | ---: |
| 2019 D1 / D2 | 1 / 22 |
| 2020 D2 | 3 |
| 2022 D1 / D2 | 1 / 10 |
| 2023 D2 | 12 |

- **Gates:** das 61 candidatas, 12 reprovaram: letras A–E não encontradas em sequência (2019 D2 Q139; 2022 D2 Q103 e Q156; 2023 D2 Q132), glifo privado no texto (2022 D2 Q108, Q115 e Q116; 2023 D2 Q170) e tinta da linha anterior sobreposta ao cabeçalho, que o corte exato não resolve (2022 D2 Q91, Q136, Q144 e Q169). As 49 restantes foram vistas em 9 folhas de contato; todas completas, com fórmulas, frações, estruturas químicas e figuras inteiras. Todas recebem a, b, c oficiais (1399 questões com TRI).
- **Alternativas:** a regra `safe_alternativas` do lote 25 trocou as cinco alternativas pelo texto de apoio padrão em 16 das 49 (expoentes, índices ou fórmulas achatados na camada de texto); nas demais as alternativas são texto limpo.
- **Correção no construtor:** o replay de 2019 D2 Q117 (duas regiões) não reproduzia o PNG gerado, de novo por variação do cache de imagens do MuPDF (o construtor renderizava com um documento já usado por outras questões, e o replay abre um documento novo para cada questão). O construtor agora gera o PNG final com o mesmo procedimento do replay (`replay_png`: documento novo, `store_shrink(100)` e só então os painéis). O replay bate byte a byte.

```sh
python scripts/build_enem_figure_batch_report.py --batch 26
python scripts/apply_enem_batch_26.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) com expoentes e índices achatados; descrição da imagem genérica; conferência por folha de contato.
