# ENEM — lote 09: expansão do catálogo (texto puro)

Primeiro lote que **acrescenta identidades novas** além das 513 do catálogo original: **64 questões**, de 509 para **573** pontuáveis. As 509 anteriores permanecem byte a byte idênticas (`previous_lines_sha256` no relatório).

| Prova | Novas |
| --- | ---: |
| 2018 D1 / D2 | 9 / 6 |
| 2022 D1 / D2 | 6 / 7 |
| 2023 D1 / D2 | 9 / 5 |
| 2025 D1 / D2 | 17 / 5 |

## Método

1. `scripts/extract_exam_candidates.py` lê a camada de texto do **PDF oficial** (não o fused), segmenta cada questão (cabeçalho até o próximo cabeçalho, com continuação em outra coluna/página), separa base, comando e alternativas A–E, recompõe parágrafos e lê o **gabarito oficial** do PDF.
2. Só entram questões "tier A": cinco alternativas, nenhuma imagem/desenho relevante, nenhum sobrescrito/índice, sem poesia, sem numeração de linhas, sem texto compartilhado entre questões, sem hifenização, uma única região.
3. **Corroboração de identidade:** a resposta do fused tem de coincidir com o gabarito oficial na mesma posição. Cerca de metade das posições não auditadas diverge (ver abaixo) e **fica de fora**.
4. Cada região foi conferida visualmente em folhas de contato (completa, sem figuras, sem texto de outra questão). Um poema curto (2025 D2 Q95) foi retirado por exigir quebras de linha.
5. `scripts/build_enem_batch_09_report.py` grava `data/audit/batch-09-review.json`; `scripts/apply_enem_batch_09.py` reaplica tudo contra os PDFs originais (SHA-256 conferido), acrescenta as identidades ao inventário como linhas **pendentes** e só então as aprova. Cada questão guarda o recorte original (`batch09-…-source.png`) para consulta.

```sh
python scripts/build_enem_batch_09_report.py   # opcional: regenera o relatório
python scripts/apply_enem_batch_09.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Achados e limites

- **O `gabarito_oficial` do fused é pouco confiável fora das questões já auditadas:** em 2025 D1, 40 de 84 posições divergem do gabarito oficial; nas já publicadas, 0 de 15. Por isso o gabarito vem sempre do PDF oficial e a concordância com o fused é usada só como evidência de identidade.
- Não há revalidação independente de `CO_ITEM` (a tabela `ITENS_PROVA` do Inep segue indisponível). Parâmetros TRI permanecem `null`.
- A conferência visual foi por região (folhas de contato), não pixel a pixel contra o texto extraído; o texto vem da camada de texto do PDF.
- Ficaram para os próximos lotes: posições com divergência fused × oficial (identidade a resolver), questões com figuras, fórmulas, poesia, texto compartilhado (ex.: 2025 D1 Q06–Q10) e 2024 D2 (bloqueada pelo PR #26).
- 2019, 2020 e 2021 não produziram candidatos de texto puro com o extrator atual e precisam de tratamento próprio.
