# ENEM — lote 11: 119 questões de 2019, 2020 e 2025

Catálogo: 677 → **796** pontuáveis. As 677 anteriores permanecem byte a byte idênticas (`previous_lines_sha256`).

| Prova | Novas |
| --- | ---: |
| 2019 D1 / D2 | 33 / 15 |
| 2020 D1 / D2 | 38 / 1 |
| 2025 D1 / D2 | 21 / 11 |

Mesmo método do lote 10: texto da camada de texto do PDF oficial, `co_item`/`co_habilidade`/`in_item_aban` vindos da resolução de identidade (ITENS_PROVA oficial), resposta do ITENS_PROVA igual ao gabarito do PDF, conferência visual de cada região em folhas de contato e reaplicação contra os PDFs originais com SHA-256.

```sh
python scripts/build_enem_batch_11_report.py   # opcional
python scripts/apply_enem_batch_11.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

## O que mudou no extrator
`extract_exam_candidates.py` passou a reconhecer o formato dos PDFs de 2019 e 2020: o marcador gráfico da letra da alternativa e a barra do cabeçalho de 2019 deixaram de contar como figura, e `A \t` (2020) deixou de ser ignorado. Antes, 2019 e 2020 não geravam nenhum candidato.

## Ficaram fora (decisão por questão)
- Exigem quebras de linha: 2019 D1 Q13 (diálogo teatral) e Q61 (versos), 2019 D2 Q141 (índices J₁/J₂), 2020 D1 Q12 (versos) e Q24 (decreto em artigos), 2025 D2 Q95 (poema).
- 2020 D1 Q06: a linha de título da seção ("Questões de 06 a 10") invade o topo do recorte.
- 2020 D1 Q48 e Q49: a última linha da Q48 invade a caixa do cabeçalho da Q49; recortes adjacentes que o extrator não separa. O triador de imagens (CLIP_BOTTOM/CLIP_TOP) pegou os dois, e uma correção de fronteira geral piorou 2025, então foram retirados em vez de forçar.
- 2024 D1: nenhuma candidata de texto puro nova (as 12 "tier A" já estavam aprovadas).
- 2020 D2 aplicação digital e posições 1–5 de LC (idioma).

## Limites
Conferência visual por região, não pixel a pixel; texto vem da camada de texto do PDF. Parâmetros TRI `null` nos registros; o carregador junta TRI pelo CO_ITEM resolvido.
