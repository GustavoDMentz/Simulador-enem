#!/usr/bin/env python3
"""Triagem determinística das imagens publicadas (barata, sem OCR nem IA).

Sinaliza recortes suspeitos para conferência visual posterior; NÃO aprova nem
altera nada. Detectores: imagem ausente/ilegível, hash divergente do manifesto,
quase em branco, glifos cortados na borda (CLIP_*), proporção extrema,
baixa resolução e arquivo duplicado entre questões diferentes.

Uso:
  python scripts/audit_image_quality.py [--out DIR] [--sheet]
Requer Pillow e numpy.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
IMG_RE = re.compile(r"\.(png|jpe?g)$", re.I)
INK = 200          # pixel < INK conta como tinta


def collect_refs(obj):
    if isinstance(obj, str):
        if IMG_RE.search(obj) and obj.startswith("/images/"):
            yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from collect_refs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from collect_refs(v)


def resolve(ref):
    return ROOT / "data" / "extracted" / ref[len("/images/"):]


def clipped(line):
    """Tinta na última linha/coluna em trechos curtos e dispersos = glifos cortados.
    Linhas contínuas (bordas de tabela, barra de citação) não contam."""
    n = len(line)
    if line.sum() < max(6, 0.01 * n):
        return False
    d = np.diff(np.concatenate(([0], line.astype(np.int8), [0])))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    runs = ends - starts
    return float(runs.max()) < 0.5 * n and len(runs) >= 3


def analyse(path):
    flags = []
    try:
        im = Image.open(path)
        im.load()
    except Exception as exc:  # noqa: BLE001
        return {"flags": ["UNREADABLE"], "error": str(exc)}
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, "white")
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    g = np.asarray(im.convert("L"))
    h, w = g.shape
    ink = g < INK
    frac = float(ink.mean())
    if frac < 0.002:
        flags.append("BLANK")
    if w < 300 or h < 40:
        flags.append("LOWRES")
    ar = w / h
    if ar > 8 or ar < 0.15:
        flags.append("ASPECT")
    if frac >= 0.002:
        for side, line in (("TOP", ink[0, :]), ("BOTTOM", ink[-1, :]),
                           ("LEFT", ink[:, 0]), ("RIGHT", ink[:, -1])):
            if clipped(line):
                flags.append(f"CLIP_{side}")
    return {"flags": flags, "w": w, "h": h, "ink": round(frac, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "audit" / "image-triage"))
    ap.add_argument("--sheet", action="store_true", help="gera contact sheets dos sinalizados")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in (ROOT / "data/blue-published/questions.jsonl").open(encoding="utf-8")]
    manifest = json.loads((ROOT / "data/audit/question-presentation.json").read_text(encoding="utf-8"))["questions"]

    by_file = collections.defaultdict(set)
    for r in rows:
        qid = r["id_unico_sistema"]
        for ref in collect_refs(r):
            by_file[ref].add(qid)
        for ref in collect_refs(manifest.get(qid, {})):
            by_file[ref].add(qid)

    sha_users = collections.defaultdict(set)
    results = {}
    for ref, qids in sorted(by_file.items()):
        p = resolve(ref)
        if not p.exists():
            results[ref] = {"flags": ["MISSING"], "questions": sorted(qids)}
            continue
        res = analyse(p)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        res["sha256"] = digest
        res["questions"] = sorted(qids)
        sha_users[digest].add(ref)
        results[ref] = res

    for qid, m in manifest.items():
        if m.get("source") and m.get("source_sha256") and m["source"] in results:
            if results[m["source"]].get("sha256") != m["source_sha256"]:
                results[m["source"]]["flags"].append("HASH_MISMATCH")
    for digest, refs in sha_users.items():
        if len(refs) > 1:
            for ref in refs:
                results[ref]["flags"].append("DUPLICATE_FILE")

    flagged = {k: v for k, v in results.items() if v["flags"]}
    (out / "triage.json").write_text(
        json.dumps({"total": len(results), "flagged": len(flagged), "results": results},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    counts = collections.Counter(f for v in flagged.values() for f in v["flags"])
    print(f"imagens: {len(results)} | sinalizadas: {len(flagged)}")
    for f, n in counts.most_common():
        print(f"  {f}: {n}")

    if args.sheet and flagged:
        thumbs = sorted(flagged.items())
        per = 12
        for i in range(0, len(thumbs), per):
            chunk = thumbs[i:i + per]
            cols, cw, ch = 3, 520, 330
            sheet = Image.new("RGB", (cols * cw, ((len(chunk) + cols - 1) // cols) * ch), "white")
            d = ImageDraw.Draw(sheet)
            for j, (ref, v) in enumerate(chunk):
                x, y = (j % cols) * cw, (j // cols) * ch
                try:
                    im = Image.open(resolve(ref)).convert("RGB")
                    im.thumbnail((cw - 10, ch - 40))
                    sheet.paste(im, (x + 5, y + 35))
                except Exception:  # noqa: BLE001
                    pass
                label = f"{v['questions'][0]} {','.join(v['flags'])}"
                d.text((x + 5, y + 5), label, fill="red")
                d.rectangle([x, y, x + cw - 1, y + ch - 1], outline="gray")
            sheet.save(out / f"sheet_{i // per + 1:02d}.png")
        print(f"contact sheets em {out}")


if __name__ == "__main__":
    main()
