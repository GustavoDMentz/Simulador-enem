# ENEM — lote 28: 33 questões de 2021 (texto recuperado de outros cadernos)

Catálogo: 1444 → **1477** pontuáveis. As 1444 anteriores permanecem byte a byte idênticas. É a primeira frente de **2021**, cujo caderno azul tem a camada de texto corrompida: o recorte visual é perfeito, mas parte das linhas extraídas vira lixo, e por isso 84 posições estavam de fora.

| Prova | Novas |
| --- | ---: |
| 2021 D1 | 23 |
| 2021 D2 | 10 |

## Como o texto foi recuperado
1. O CO_ITEM da posição azul vem de `data/audit/identity-resolution.json`.
2. O mesmo CO_ITEM é procurado nos cadernos rosa, amarelo, branco e cinza (ITENS_PROVA 2021 oficial). A ordem de cada caderno foi conferida contra o gabarito oficial em PDF da cor (de 85 a 90 posições iguais por caderno; 1 anulada sem letra).
3. Linha a linha vale a primeira versão sem lixo, azul primeiro. Um caderno só entra se tiver o mesmo número de linhas e coincidir nas linhas limpas de ambos.
4. As linhas que continuam corrompidas em todos os cadernos (fontes com mapeamento quebrado, em geral as mesmas de um caderno para o outro) viram lacuna ⟦?⟧ e só passam com **transcrição manual conferida na imagem**: `data/audit/text-recovery-2021-fills.json` (um preenchimento por lacuna, na ordem). Questão com lacuna sem transcrição não entra.

Recorte, gabarito e identidade continuam sendo do caderno azul; os outros cadernos só fornecem texto de apoio (comando, base e alternativas em cartões).

- **Aprovadas:** das 84 posições pendentes, 33 tinham no máximo 3 lacunas (4 sem nenhuma). Todas passaram nos gates e foram vistas em 6 folhas de contato: todas completas. Correções de texto conferidas na imagem em 2021 D1 Q43 e D2 Q130 e Q144 (`TEXT_OVERRIDES`).
- **TRI:** 32 das 33 recebem a, b, c oficiais (1463 questões com TRI); a 2021 D1 Q43 não tem parâmetros no ITENS_PROVA oficial.
- **Faltam em 2021:** 51 posições (mais de 3 lacunas ou sem texto aproveitável): ficam para um lote seguinte, com mais transcrição.

```sh
python scripts/recover_2021_text.py --itens ITENS_PROVA_2021.csv --pdf-dir DIR_DOS_CADERNOS --out data/audit/text-recovery-2021.json
python scripts/build_enem_figure_batch_report.py --batch 28
python scripts/apply_enem_batch_28.py --pdf-root data/enem-pdfs/oficiais
python scripts/build_question_presentation.py
python -m pytest -q tests scripts/tests && node --test web/tests/*.test.js
```

`ITENS_PROVA_2021.csv` (SHA-256 em `data/audit/identity/sources.json`) e os cadernos de cor (`2021_PV_impresso_D{1,2}_CD{2,3,4,5,6,8}.pdf` e os gabaritos `GB`) vêm do Inep; as URLs e SHA-256 ficam em `data/audit/text-recovery-2021.json`.

## Limites
Texto de apoio (comando e base ocultos na tela, lidos por leitores de tela) com linhas transcritas à mão e justificações largas que fragmentam algumas linhas; descrição da imagem genérica; conferência por folha de contato.
