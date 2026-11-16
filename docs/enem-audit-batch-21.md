# ENEM — lote 21: 54 questões em duas regiões (grupo C)

Catálogo: 1218 → **1272** pontuáveis. As 1218 anteriores permanecem byte a byte idênticas. Primeiro lote da fase 2: questões que continuam em outra coluna ou página, com cinco alternativas em texto. O recorte é feito por região e as regiões são **empilhadas** na ordem de leitura em um único PNG (o replay dos lotes já aceitava uma lista de regiões).

| Prova | Novas |
| --- | ---: |
| 2017 D1 / D2 | 9 / 1 |
| 2018 D1 / D2 | 7 / 3 |
| 2019 D1 / D2 | 7 / 3 |
| 2020 D1 | 7 |
| 2022 D1 | 9 |
| 2023 D1 | 8 |

- **Construtor:** `scripts/build_enem_figure_batch_report.py` agora aceita várias regiões por questão: cada uma vira um painel com a mesma caixa (texto, imagens e desenhos, sem marcas de margem, estendida até conter as linhas cortadas), e os painéis são colados de cima para baixo. Os gates rodam em todos os painéis, e o hash do texto de origem junta as regiões.
- **Seleção:** 60 candidatas com duas regiões, cinco alternativas, identidade corroborada e sem fórmulas ou idioma. **6 reprovaram nos gates** e ficaram de fora: 2017 D1 Q35, 2020 D1 Q13, e 2025 D1 Q16, Q44, Q50 e Q67. Nelas o painel traz um pedaço da questão anterior (alternativas D e E, ou o cabeçalho da seguinte); em 2025 D1 o cabeçalho "Questão n" da questão vizinha cai dentro da segunda região. É o mesmo problema de fronteira do lote 20.
- **Verificação:** as 60 foram vistas em folhas de contato empilhadas (as 54 aprovadas estão completas e a continuação aparece logo abaixo, sem sobreposição) e conferi um recorte final. As 54 recebem a, b, c oficiais (1262 questões com TRI).

```sh
python scripts/build_enem_figure_batch_report.py --batch 21
python scripts/apply_enem_batch_21.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio da camada do PDF (agora das regiões somadas), descrição da imagem genérica, conferência por folha de contato.
