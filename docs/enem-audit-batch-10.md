# ENEM — lote 10: 104 questões de 2018 e 2023 com identidade resolvida

Catálogo: 573 → **677** pontuáveis. As 573 anteriores permanecem byte a byte idênticas (`previous_lines_sha256`).

| Prova | Novas |
| --- | ---: |
| 2018 D1 / D2 | 30 / 11 |
| 2023 D1 / D2 | 48 / 15 |

## O que é diferente do lote 09
O lote 09 só aceitava questões em que o fused concordava com o gabarito oficial (evidência indireta de identidade). Aqui a identidade é **resolvida**: [docs/identity-resolution.md](identity-resolution.md) identifica, no ITENS_PROVA oficial, o único CO_PROVA azul cujo gabarito é igual ao gabarito do PDF, e daí vêm `co_item`, `co_habilidade` e `in_item_aban`. O fused não é usado. Por isso entram também posições que o lote 09 deixou de fora por divergência fused × oficial, e posições que nem existiam no fused.

## Método (igual ao lote 09)
`extract_exam_candidates.py` → conferência visual de cada região em folhas de contato → `build_enem_batch_10_report.py` grava `data/audit/batch-10-review.json` → `apply_enem_batch_10.py` reaplica contra os PDFs originais (SHA-256 conferido), confere resposta e CO_ITEM contra a resolução de identidade, acrescenta as identidades ao inventário como pendentes e só então as aprova.

Condições de entrada: texto puro, cinco alternativas, sem figura/desenho/sobrescrito, região única, `tx_gabarito` do ITENS_PROVA = gabarito do PDF. Ficaram fora, por exigirem quebras de linha: 2018 D1 Q08 (diálogo) e 2023 D1 Q19 (estrofe).

```sh
python scripts/build_enem_batch_10_report.py   # opcional
python scripts/apply_enem_batch_10.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## Limites
- Parâmetros TRI continuam `null` nos registros; o carregador junta TRI pelo CO_ITEM resolvido.
- Conferência visual por região, não pixel a pixel; o texto vem da camada de texto do PDF.
- Só 2018 e 2023 têm identidade resolvida. 2019, 2020, 2024 e 2025 dependem do mesmo cruzamento (zip de 2025 recusou conexão).
- Posições 1–5 de LC (idioma inglês/espanhol) não entram.
