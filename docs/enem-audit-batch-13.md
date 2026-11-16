# ENEM — lote 13: 33 questões com versos e textos de leitura curta (2017–2025)

Catálogo: 903 → **936** pontuáveis. As 903 anteriores permanecem byte a byte idênticas.

| Prova | Novas |
| --- | ---: |
| 2017 D1 | 8 |
| 2018 D1 | 3 |
| 2019 D1 / D2 | 9 / 1 |
| 2020 D1 | 6 |
| 2022 D1 | 1 |
| 2023 D1 | 4 |
| 2025 D1 | 1 |

São as candidatas que o extrator marcava só como `possivel_poesia`, de região única e cinco alternativas. 15 são prosa (o sinal era só de coluna estreita) e 18 são versos, cujo `texto_base` agora guarda as quebras de linha lidas da camada de texto do PDF, conferidas contra o texto do extrator (mesmas palavras, ignorando espaços e hifens). Demais passos como no lote 12 (identidade pelo ITENS_PROVA, gabarito do PDF = ITENS_PROVA, conferência visual em folhas de contato, replay com SHA-256).

```sh
python scripts/build_enem_batch_13_report.py
python scripts/apply_enem_batch_13.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Ficaram fora
2017 D1 Q09 e 2020 D1 Q74 (versos e prosa no mesmo recorte), 2017 D1 Q27 (glossário em linhas soltas), 2019 D1 Q72 (artigos e incisos) e Q78 (dois versos dentro de um texto em prosa).

## 2021
Os PDFs de 2021 têm a camada de texto corrompida (64% dos caracteres inválidos em D1, 27% em D2); só entram por imagem ou OCR.

## Limites
As quebras de estrofe são aproximadas (detectadas pelo espaçamento vertical); a exibição ao aluno continua sendo o recorte do PDF. TRI `null`.
