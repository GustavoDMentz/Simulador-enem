# ENEM — lote 27: 34 questões com fórmulas de 2024 e 2025

Catálogo: 1410 → **1444** pontuáveis. As 1410 anteriores permanecem byte a byte idênticas. Terceiro e último lote das questões separadas só por conterem expoentes, índices ou fórmulas (`sobrescrito_ou_indice`), mesmo método dos lotes 25 e 26.

| Prova | Novas |
| --- | ---: |
| 2024 D2 | 17 |
| 2025 D1 / D2 | 1 / 16 |

- **Gates:** das 43 candidatas, 8 reprovaram: tinta da linha anterior sobreposta ao cabeçalho (2024 D2 Q99, Q114, Q116, Q136, Q151 e Q180), letras A–E não encontradas em sequência (2024 D2 Q148) e glifo privado no texto (2025 D2 Q160). Das 35 restantes, **2025 D2 Q130** saiu na conferência visual: a segunda região é a faixa do cabeçalho da página ("Exame Nacional do Ensino Médio") e traz esse texto para dentro do recorte (a mesma região de continuação espúria dos lotes 23). As 34 foram vistas em 6 folhas de contato; todas completas. Todas recebem a, b, c oficiais (1431 questões com TRI).
- **Alternativas:** `safe_alternativas` trocou as cinco alternativas pelo texto de apoio padrão em 10 das 35 aprovadas nos gates (expoentes, índices ou fórmulas achatados na camada de texto).

```sh
python scripts/build_enem_figure_batch_report.py --batch 27
python scripts/apply_enem_batch_27.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) com expoentes e índices achatados; descrição da imagem genérica; conferência por folha de contato.
