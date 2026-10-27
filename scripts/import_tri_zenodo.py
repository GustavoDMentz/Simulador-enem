#!/usr/bin/env python3
"""Reproducible, checksum-pinned TRI import from Zenodo's INEP ITENS_PROVA mirror.

Only exact (year, CO_ITEM, SG_AREA, TX_GABARITO) matches with one unambiguous
finite (a,b,c) triple are released. The published question catalog is read-only.
"""
import collections
import csv
import hashlib
import io
import json
import math
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/blue-published/questions.jsonl"
OUTPUT = ROOT / "data/tri/parametros-oficiais.jsonl"
REPORT = ROOT / "data/audit/tri-zenodo-import-review.json"
RECORD = "https://zenodo.org/records/18801899/files/"
FILES = {
    2018: ("2018 ITENS PROVA ENEM.csv", "5487ab28cc2dac3f27dd06974ee4b5a4"),
    2019: ("2019 ITENS PROVA ENEM.csv", "d170738f168755aebcffd10cde468b83"),
    2020: ("2020 ITENS PROVA ENEM.csv", "633746122218dc1e47e4aa1ddae6dd0e"),
    2021: ("2021 ITENS PROVA ENEM.csv", "0734c69fb976c9d1b533665b1ad8d306"),
    2022: ("2022 ITENS PROVA ENEM.csv", "52013f06fbce11f5d6731ee2a8d25bfc"),
    2023: ("2023 ITENS PROVAS ENEM.csv", "1e086f7786afe964a744a13c8b64c6df"),
}
REQUIRED = {"CO_ITEM", "SG_AREA", "TX_GABARITO", "IN_ITEM_ABAN", "NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"}


def canonical_item(value):
    value = str(value if value is not None else "").strip()
    return str(int(value)) if value.isdecimal() else None


def number(value):
    try:
        n = float(str(value).strip().replace(",", "."))
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def download(year, name, md5):
    url = RECORD + urllib.parse.quote(name) + "?download=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Simulador-enem-TRI-import/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError(f"{year}: unexpected file size")
    digest = hashlib.md5(payload).hexdigest()
    if digest != md5:
        raise ValueError(f"{year}: checksum mismatch: {digest} != {md5}")
    # These CSV files originate from INEP microdata; latin-1 preserves their bytes.
    text = payload.decode("utf-8-sig") if payload.startswith(b"\xef\xbb\xbf") else payload.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
        # Support comma-separated mirrors only if all required columns are present.
        reader = csv.DictReader(io.StringIO(text), delimiter=",")
    if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
        raise ValueError(f"{year}: missing required columns; got {reader.fieldnames}")
    return list(reader), url


def main():
    questions = [json.loads(line) for line in CATALOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates, blocked, provenance = [], [], {}
    seen = set()
    for year, (filename, digest) in FILES.items():
        rows, url = download(year, filename, digest)
        provenance[str(year)] = {"filename": filename, "md5": digest, "url": url, "source_rows": len(rows)}
        by_item = collections.defaultdict(list)
        for row in rows:
            key = canonical_item(row.get("CO_ITEM"))
            if key:
                by_item[key].append(row)
        for q in questions:
            if q.get("ano") != year:
                continue
            item = canonical_item(q.get("co_item"))
            key = (year, item)
            if not item or key in seen:
                blocked.append({"id": q.get("id_unico_sistema"), "ano": year, "co_item": item, "reason": "missing or duplicate catalog identity"})
                continue
            seen.add(key)
            eligible = set()
            source_matches = by_item.get(item, [])
            for row in source_matches:
                if row["SG_AREA"].strip().upper() != q.get("area_conhecimento"):
                    continue
                if row["TX_GABARITO"].strip().upper() != q.get("gabarito_oficial"):
                    continue
                if row["IN_ITEM_ABAN"].strip() != "0":
                    continue
                triple = tuple(number(row["NU_PARAM_" + letter]) for letter in "ABC")
                a, b, c = triple
                if any(v is None for v in triple) or a <= 0 or not 0 <= c <= 1:
                    continue
                eligible.add(triple)
            if len(eligible) != 1:
                blocked.append({"id": q.get("id_unico_sistema"), "ano": year, "co_item": item,
                                "reason": "no unique compatible parameter triple", "source_matches": len(source_matches),
                                "eligible_triples": len(eligible)})
                continue
            a, b, c = next(iter(eligible))
            candidates.append({"ano": year, "co_item": int(item), "area_conhecimento": q["area_conhecimento"],
                               "gabarito_oficial": q["gabarito_oficial"], "a": a, "b": b, "c": c,
                               "fonte": f"INEP ITENS_PROVA via Zenodo 10.5281/zenodo.18801899 ({digest})",
                               "status": "VERIFIED"})
    candidates.sort(key=lambda p: (p["ano"], p["co_item"]))
    report = {"source": "https://doi.org/10.5281/zenodo.18801899", "provenance": provenance,
              "catalog_questions": len(questions), "matched": len(candidates),
              "blocked_count": len(blocked), "blocked": blocked,
              "note": "VERIFIED means exact catalog identity and unique valid parameters from checksum-pinned microdata; not independent PDF certification."}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(p, ensure_ascii=False, separators=(",", ":")) + "\n" for p in candidates), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"catalog_questions": len(questions), "matched": len(candidates), "blocked": len(blocked)}, ensure_ascii=False))
    if not candidates:
        raise SystemExit("No verified matches: refusing empty import")


if __name__ == "__main__":
    main()
