#!/usr/bin/env python3
"""Gera data/tri/parametros-oficiais.jsonl a partir do ITENS_PROVA OFICIAL do Inep (colunas NU_PARAM_A/B/C).

Não estima nada: só copia parâmetros que o Inep publica, para os itens cuja identidade foi resolvida
(data/audit/identity-resolution.json). Cada registro exige que, na linha oficial do CO_PROVA escolhido,
o CO_ITEM, a área e o gabarito coincidam com a resolução de identidade. Itens sem parâmetros no CSV
(anulados, abandonados) ficam de fora e são listados em data/tri/official-sources.json.

Uso: python scripts/build_official_tri.py DIR   (DIR/ANO/ITENS_PROVA_ANO.csv, de scripts/fetch_inep_itens_prova.py)
O SHA-256 de cada CSV bruto é conferido contra data/audit/identity/sources.json.
"""
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def num(v):
    try:
        n = float(str(v or "").strip().replace(",", "."))
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def main(base):
    ident = json.loads((ROOT / "data/audit/identity-resolution.json").read_text())["items"]
    sources = json.loads((ROOT / "data/audit/identity/sources.json").read_text())["sources"]
    out, skipped, report = [], [], {}
    for year in range(2017, 2026):
        raw = (Path(base) / str(year) / f"ITENS_PROVA_{year}.csv").read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == sources[str(year)]["csv_sha256"], f"SHA-256 diverge em {year}"
        rows = list(csv.DictReader(io.StringIO(raw.decode("latin-1")), delimiter=";", quoting=csv.QUOTE_NONE))
        by_item = {}
        for r in rows:
            by_item.setdefault((r["CO_PROVA"], r["CO_ITEM"]), r)
        seen, n = {}, 0
        for uid, it in sorted(ident.items()):
            if not uid.startswith(str(year)):
                continue
            r = by_item.get((str(it["co_prova"]), str(it["co_item"])))
            assert r is not None, f"item oficial ausente: {uid}"
            assert r["TX_GABARITO"] == it["tx_gabarito"] and r["SG_AREA"] == it["area"], f"identidade diverge: {uid}"
            a, b, c = (num(r[k]) for k in ("NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"))
            if None in (a, b, c) or a <= 0 or not 0 <= c <= 1 or r["TX_GABARITO"] not in "ABCDE" or not r["TX_GABARITO"]:
                skipped.append(dict(id=uid, ano=year, co_item=it["co_item"], motivo="sem parâmetros oficiais válidos (anulado/abandonado)"))
                continue
            key = (year, it["co_item"])
            rec = dict(ano=year, co_item=it["co_item"], area_conhecimento=it["area"], gabarito_oficial=r["TX_GABARITO"],
                       a=a, b=b, c=c, fonte=f"INEP ITENS_PROVA_{year} (microdados_enem_{year}.zip; CSV sha256 {digest[:16]})",
                       status="VERIFIED")
            if key in seen:
                assert seen[key] == rec, f"registros conflitantes: {key}"
                continue
            seen[key] = rec
            out.append(rec); n += 1
        report[str(year)] = dict(url=sources[str(year)]["url"], entry=sources[str(year)]["entry"], csv_sha256=digest, items=n)
    (ROOT / "data/tri/parametros-oficiais.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    (ROOT / "data/tri/official-sources.json").write_text(json.dumps(dict(
        note="Parâmetros a, b, c copiados do ITENS_PROVA oficial do Inep, sem estimativa. Só itens da identidade resolvida.",
        years=report, skipped_without_params=skipped), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(out), "itens oficiais;", len(skipped), "sem parâmetros")


if __name__ == "__main__":
    main(sys.argv[1])
