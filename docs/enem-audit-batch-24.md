# ENEM — lote 24: 9 questões de fronteira (a questão anterior colada no cabeçalho)

Catálogo: 1305 → **1314** pontuáveis. As 1305 anteriores permanecem byte a byte idênticas.

| Prova | Novas |
| --- | ---: |
| 2017 D1 (Q35) | 1 |
| 2020 D1 (Q06, Q13, Q14, Q22, Q25, Q26, Q48, Q49) | 8 |

São as questões que ficaram de fora dos lotes 11, 20 e 21 porque a última linha da questão anterior fica colada ao cabeçalho "Questão n" e entrava no recorte.

- **Corte exato no cabeçalho (`trim_to_header`):** as caixas de texto das duas linhas se sobrepõem em até ~2 pt, mas a tinta não. O construtor calcula, pela linha base e pelo tamanho da fonte, onde termina a tinta da linha anterior (linha base + descendente) e onde começa a tinta do cabeçalho (linha base − altura das maiúsculas) e corta no meio do vão. Se as tintas se sobrepuserem, a questão reprova.
- **Gates e extensão pela tinta:** a extensão das linhas cortadas e os gates passaram a usar a mesma medida de tinta (em vez da fração da caixa da linha), para a base e para o topo. Isso resolveu também a última linha de Q13, Q25 e Q48, que antes não podia ser incluída por colidir com o cabeçalho seguinte.
- **Verificação:** 9 recortes em folhas de contato; todos começam exatamente em "Questão n" e terminam com a última linha inteira. Os gates não reprovaram nenhum. Todas recebem a, b, c oficiais (1303 questões com TRI).
- **Ainda fora:** 2025 D1 Q16, Q44, Q50 e Q67, cujo problema é outro: a segunda região cobre as duas colunas da página e traz o cabeçalho da questão vizinha.

```sh
python scripts/build_enem_figure_batch_report.py --batch 24
python scripts/apply_enem_batch_24.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos dos lotes anteriores: texto de apoio da camada do PDF, descrição da imagem genérica, conferência por folha de contato.
