# TRI — parâmetros a, b, c oficiais

Os parâmetros vêm **só** do `ITENS_PROVA` oficial do Inep (colunas `NU_PARAM_A/B/C` de `microdados_enem_ANO.zip`). A base externa de terceiros (`external-staging`, derivada de `HenriqueLindemann/analise-enem`) foi **removida**: tinha 150 divergências de gabarito e nenhuma procedência verificada.

## Como é gerado
```sh
for y in 2017 2018 2019 2020 2021 2022 2023 2024 2025; do
  python scripts/fetch_inep_itens_prova.py --year $y --out-dir DIR/$y
done
python scripts/build_official_tri.py DIR
```
- O download é por HTTP range, só da entrada `ITENS_PROVA_ANO.csv`, com CRC32 conferido; o SHA-256 de cada CSV bruto é conferido contra `data/audit/identity/sources.json`.
- `scripts/build_official_tri.py` copia os parâmetros dos itens cuja identidade foi resolvida (`data/audit/identity-resolution.json`), exigindo que `CO_ITEM`, área e gabarito da linha oficial do `CO_PROVA` escolhido coincidam com a resolução. Nada é estimado.
- Saídas: `data/tri/parametros-oficiais.jsonl` (1514 itens, `status: VERIFIED`) e `data/tri/official-sources.json` (URL, entrada e SHA-256 por ano, e os 26 itens sem parâmetros oficiais: anulados ou abandonados).

## No app
`web/published-questions.js` junta o TRI pelo `CO_ITEM` resolvido. Das 936 questões publicadas, **856** recebem a, b, c oficiais. As 72 sem identidade resolvida (2020 D2 digital e posições 1–5 de LC, por exemplo) e as 8 sem parâmetros oficiais ficam sem TRI. Se o gabarito ou a área divergirem da linha oficial, a junção lança erro.
