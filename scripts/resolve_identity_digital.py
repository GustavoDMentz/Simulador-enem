#!/usr/bin/env python3
"""Resolve o CO_ITEM das questões de 2020 D2 publicadas a partir da APLICAÇÃO DIGITAL, pelo ITENS_PROVA oficial.

Essas 35 questões (manifesto: application = digital) não pertencem ao caderno regular que resolve as demais.
Aqui o caderno certo é achado como nas outras provas: entre os CO_PROVA azuis de CN e de MT, só um tem a
sequência de respostas igual ao gabarito oficial digital (2020_GB_digital_D2_CD7.pdf, SHA-256 conferido com o
manifesto); os outros ficam muito abaixo. Cada questão só é aceita se a resposta do ITENS_PROVA, a letra do
gabarito oficial digital e o gabarito publicado coincidirem. Acrescenta os itens (com aplicacao = digital) a
data/audit/identity-resolution.json (idempotente); nada em questions.jsonl muda.

Uso: python scripts/resolve_identity_digital.py --key CAMINHO/2020_GB_digital_D2_CD7.pdf
"""
import argparse
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_official_gabaritos import extract_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIN_MATCH, MAX_OTHER = 0.97, 0.6
AREAS = {"CN": (91, 135), "MT": (136, 180)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", type=Path, required=True)
    args = ap.parse_args()
    manifest = {e["id"]: e for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]}
    digital = {u: e for u, e in manifest.items() if e.get("application") == "digital" and e["year"] == 2020 and e["day"] == 2}
    sha = {e["answer_source_sha256"] for e in digital.values()}
    assert len(sha) == 1 and hashlib.sha256(args.key.read_bytes()).hexdigest() in sha, "gabarito digital diferente do registrado no manifesto"
    keymap, ambiguous, _ = extract_pdf(args.key)
    key = {n: v["comum"] for n, v in keymap.items() if "comum" in v}
    rows = list(csv.DictReader((ROOT / "data/audit/identity/itens-prova-2020-azul.csv").open(encoding="utf-8"), delimiter=";"))
    by = collections.defaultdict(list)
    for r in rows:
        if r["SG_AREA"] in AREAS:
            by[(r["CO_PROVA"], r["SG_AREA"])].append(r)
    release = {json.loads(l)["id_unico_sistema"]: json.loads(l) for l in (ROOT / "data/blue-published/questions.jsonl").read_text().splitlines()}
    path = ROOT / "data/audit/identity-resolution.json"
    ident = json.loads(path.read_text())
    chosen, evidence, added, problems = {}, [], {}, []
    for area in AREAS:
        scored = []
        for (prova, a), rs in by.items():
            if a != area:
                continue
            comp = [r for r in rs if key.get(int(r["CO_POSICAO"])) in tuple("ABCDE") and r["TX_GABARITO"] in tuple("ABCDE")]
            m = sum(1 for r in comp if key[int(r["CO_POSICAO"])] == r["TX_GABARITO"])
            scored.append((m / len(comp) if comp else 0.0, m, len(comp), prova))
        scored.sort(reverse=True)
        ok = scored[0][0] >= MIN_MATCH and all(s[0] <= MAX_OTHER for s in scored[1:])
        evidence.append(dict(area=area, chosen_co_prova=scored[0][3] if ok else None, resolved=ok,
                             candidates=[dict(co_prova=s[3], agree=s[1], compared=s[2], ratio=round(s[0], 3)) for s in scored]))
        if ok:
            chosen[area] = scored[0][3]
    for uid, e in sorted(digital.items()):
        q, pos = release[uid], e["number"]
        area = next((a for a, (lo, hi) in AREAS.items() if lo <= pos <= hi), None)
        if area not in chosen:
            problems.append((uid, "caderno digital não resolvido")); continue
        match = [r for r in by[(chosen[area], area)] if int(r["CO_POSICAO"]) == pos]
        if len(match) != 1:
            problems.append((uid, f"linhas oficiais={len(match)}")); continue
        r = match[0]
        if not (r["TX_GABARITO"] == key.get(pos) == q["gabarito_oficial"]):
            problems.append((uid, f"respostas divergem: itens={r['TX_GABARITO']} pdf={key.get(pos)} publicado={q['gabarito_oficial']}")); continue
        added[uid] = dict(co_item=int(r["CO_ITEM"]), co_habilidade=int(r["CO_HABILIDADE"]) if r["CO_HABILIDADE"] else None,
                          in_item_aban=int(r["IN_ITEM_ABAN"] or 0), area=area, tx_gabarito=r["TX_GABARITO"],
                          co_prova=int(chosen[area]), official_key=key[pos], aplicacao="digital")
    ident["items"].update(added)
    ident["digital_resolution"] = dict(
        method="2020 D2 aplicação digital: CO_PROVA azul cuja sequência de respostas é a do gabarito oficial digital; resposta do ITENS_PROVA = gabarito digital = gabarito publicado",
        key_sha256=sorted(sha)[0], key_url=next(iter(digital.values()))["answer_source_url"], evidence=evidence, resolved=len(added),
        published_with_wrong_co_item=sum(1 for u in added if release[u]["co_item"] != added[u]["co_item"]),
        unresolved=[dict(id=u, motivo=m) for u, m in problems])
    path.write_text(json.dumps(ident, ensure_ascii=False, indent=1) + "\n")
    print(len(added), "resolvidas;", len(problems), "pendentes")
    for u, m in problems:
        print(" ", u, m)


if __name__ == "__main__":
    main()
