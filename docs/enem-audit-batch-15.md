# ENEM — lote 15: 55 questões com figura de 2018

Catálogo: 999 → **1054** pontuáveis. As 999 anteriores permanecem byte a byte idênticas. Segundo lote da fase de figuras (grupo A), mesmo método do lote 14 (`docs/enem-audit-batch-14.md`).

| Prova | Novas |
| --- | ---: |
| 2018 D1 | 30 |
| 2018 D2 | 25 |

- **Verificação:** 55 recortes em 10 folhas de contato; os gates automáticos (nenhuma linha cortada, nenhum cabeçalho de outra questão, resposta do `ITENS_PROVA` = gabarito do PDF) não reprovaram nenhuma. As 55 recebem a, b, c oficiais (1046 questões com TRI).
- **Correção de texto (2):** 2018 D2 Q136 e Q152 traziam glifos privados de fórmula (colchetes da matriz e o símbolo de conjunto) na camada de texto. Como o texto do comando é lido por leitores de tela quando a questão é exibida como recorte, foram corrigidos conferindo a imagem: Q152 ganhou `ℕ × ℕ`, e na Q136 o comando ficou só com a frase final e a matriz A passou a ser indicada como "apresentada na imagem" (os números da matriz não saem em ordem confiável da camada de texto). As correções estão em `TEXT_OVERRIDES` do construtor e em `manual_text_overrides` do relatório. O construtor agora reprova qualquer glifo privado no texto.

```sh
python scripts/build_enem_figure_batch_report.py --batch 15
python scripts/apply_enem_batch_15.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
Os mesmos do lote 14: texto de apoio com rótulos de figuras, descrição da imagem genérica, conferência por folha de contato.
