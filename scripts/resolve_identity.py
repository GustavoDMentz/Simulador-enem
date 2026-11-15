#!/usr/bin/env python3
"""Resolve a identidade (CO_ITEM) de cada posição do caderno azul regular.

O ITENS_PROVA oficial traz vários CO_PROVA por cor/área (regular, reaplicação, PPL...). O caderno do
PDF que auditamos é o único cuja sequência de respostas coincide com o gabarito oficial do PDF.
Para cada (ano, dia, área) escolhe-se o CO_PROVA azul que bate com o gabarito (>= 97% das posições
comparáveis, e nenhum outro acima de 60%); só então posição -> CO_ITEM é aceito.

Uso: python scripts/resolve_identity.py --years 2018 2023 --out data/audit/identity-resolution.json
"""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_official_gabaritos import extract_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AREAS = {1: ("LC", "CH"), 2: ("CN", "MT")}
MIN_MATCH, MAX_OTHER = 0.97, 0.60


def resolve_year(year):
    rows = list(csv.DictReader((ROOT / f"data/audit/identity/itens-prova-{year}-azul.csv").open(encoding="utf-8"), delimiter=";"))
    by_prova = collections.defaultdict(list)
    for r in rows:
        by_prova[(r["CO_PROVA"], r["SG_AREA"])].append(r)
    out, evidence = {}, []
    for day, areas in AREAS.items():
        key_pdf = ROOT / f"data/enem-pdfs/oficiais/{year}-regular-d{day}-azul-gabarito.pdf"
        if not key_pdf.exists():
            evidence.append(dict(year=year, day=day, area=None, resolved=False, note="gabarito oficial local ausente"))
            continue
        keymap, ambiguous, _ = extract_pdf(key_pdf)
        key = {n: v["comum"] for n, v in keymap.items() if "comum" in v}
        for area in areas:
            scored = []
            for (prova, a), rs in by_prova.items():
                if a != area:
                    continue
                comp = [r for r in rs if not (area == "LC" and int(r["CO_POSICAO"]) <= 5) and int(r["CO_POSICAO"]) in key]
                m = sum(1 for r in comp if key[int(r["CO_POSICAO"])] == r["TX_GABARITO"])
                scored.append((m / len(comp) if comp else 0.0, m, len(comp), prova))
            scored.sort(reverse=True)
            best = scored[0]
            ok = best[0] >= MIN_MATCH and all(s[0] <= MAX_OTHER for s in scored[1:])
            evidence.append(dict(year=year, day=day, area=area, chosen_co_prova=best[3] if ok else None, resolved=ok,
                                 candidates=[dict(co_prova=s[3], agree=s[1], compared=s[2], ratio=round(s[0], 3)) for s in scored]))
            if not ok:
                continue
            for r in by_prova[(best[3], area)]:
                pos = int(r["CO_POSICAO"])
                if area == "LC" and pos <= 5:
                    continue  # posições 1-5 têm variante de idioma; não resolvidas aqui
                uid = f"{year}_AZUL_D{day}_Q{pos:02d}"
                out[uid] = dict(co_item=int(r["CO_ITEM"]), co_habilidade=int(r["CO_HABILIDADE"]) if r["CO_HABILIDADE"] else None,
                                in_item_aban=int(r["IN_ITEM_ABAN"] or 0), area=area, tx_gabarito=r["TX_GABARITO"],
                                co_prova=int(best[3]), official_key=key.get(pos))
    return out, evidence


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "data/audit/identity-resolution.json")
    args = ap.parse_args()
    items, evidence = {}, []
    for y in args.years:
        i, e = resolve_year(y)
        items.update(i)
        evidence += e
    sources = json.loads((ROOT / "data/audit/identity/sources.json").read_text())["sources"]
    # itens de outras aplicações (digital/reaplicação) não pertencem ao caderno regular do PDF: ficam sem resolução
    manifest = json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]
    other_app = {e["id"] for e in manifest if e.get("application") not in (None, "regular")}
    skipped = sorted(u for u in items if u in other_app)
    items = {u: v for u, v in items.items() if u not in other_app}
    release = {json.loads(l)["id_unico_sistema"]: json.loads(l) for l in (ROOT / "data/blue-published/questions.jsonl").read_text().splitlines()}
    diff = [uid for uid in items if uid in release and release[uid]["co_item"] != items[uid]["co_item"]]
    same = [uid for uid in items if uid in release and release[uid]["co_item"] == items[uid]["co_item"]]
    report = dict(schema_version=1, method="official ITENS_PROVA; azul CO_PROVA whose answer sequence equals the official key",
                  thresholds=dict(min_match=MIN_MATCH, max_other=MAX_OTHER), sources={str(y): sources[str(y)] for y in args.years},
                  evidence=evidence, skipped_other_application=skipped, published_with_wrong_co_item=len(diff), published_with_correct_co_item=len(same),
                  items=dict(sorted(items.items())))
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"resolvidos {len(items)} itens; publicados com CO_ITEM errado: {len(diff)}, certo: {len(same)}")
    for e in evidence:
        print(e["year"], f"D{e['day']}", e["area"], "->", e.get("chosen_co_prova"), (e.get("candidates") or [e.get("note")])[0])


if __name__ == "__main__":
    main()
