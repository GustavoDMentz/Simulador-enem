# ENEM — lote 25: 47 questões com fórmulas de 2017 D2 e 2018 D2

Catálogo: 1314 → **1361** pontuáveis. As 1314 anteriores permanecem byte a byte idênticas. Primeiro lote das questões que o extrator separava só por conterem expoentes, índices ou fórmulas (`sobrescrito_ou_indice`), mesmo método dos lotes 14 a 24.

| Prova | Novas |
| --- | ---: |
| 2017 D2 (26 candidatas, 2 reprovadas) | 24 |
| 2018 D2 (25 candidatas, 2 reprovadas) | 23 |

- **Verificação:** 51 candidatas, 4 reprovaram nos gates (2017 D2 Q121 e 2018 D2 Q173: letras A–E não encontradas em sequência; 2017 D2 Q136: glifo privado no texto; 2018 D2 Q126: cabeçalho da questão 125 dentro do recorte). As 47 restantes foram vistas em 8 folhas de contato; todas completas, com fórmulas, frações e estruturas químicas inteiras. Todas recebem a, b, c oficiais (1350 questões com TRI).
- **Regra nova para as alternativas (`safe_alternativas`):** a camada de texto achata expoentes e índices ("x2 + y2 = 16", "16o", "C C 4 2 6 2 2 2 ×", "2,5 × 105"), e as alternativas aparecem como cartões na tela. Se qualquer texto de alternativa de uma questão com fórmulas for suspeito (letra colada em número, `×`, `=`, `<`, `>`, sobrescritos Unicode), as cinco recebem o texto de apoio padrão ("Alternativa X: reprodução gráfica oficial."); o recorte mostra as alternativas corretas. Isso ocorreu em 15 das 47 (campo `options_replaced_by_placeholder` do relatório). Nas demais as alternativas são texto limpo.
- **Texto de apoio:** o comando e a base (que ficam ocultos na tela e servem a leitores de tela) vêm da camada de texto e podem trazer expoentes e índices achatados ou rótulos de figuras.

```sh
python scripts/build_enem_figure_batch_report.py --batch 25
python scripts/apply_enem_batch_25.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio com expoentes e índices achatados; descrição da imagem genérica; conferência por folha de contato.
