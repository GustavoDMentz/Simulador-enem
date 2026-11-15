#!/usr/bin/env python3
"""Refaz recortes que cortam linhas de texto na borda, direto do PDF oficial.

Para cada imagem sinalizada como CLIP_* por audit_image_quality.py, localiza a
página/caixa registrada nos relatórios de auditoria, estende a caixa apenas o
suficiente para conter por inteiro as linhas de texto cruzadas pela borda e
renderiza de novo (mesma escala). Valida que as linhas do miolo continuam
idênticas pixel a pixel ao recorte antigo.

Uso:
  python scripts/fix_clipped_crops.py --triage triage.json            # simulação
  python scripts/fix_clipped_crops.py --triage triage.json --apply    # grava
Requer PyMuPDF, Pillow e numpy. Os PDFs vêm de data/enem-pdfs/oficiais.
"""
import argparse
import glob
import hashlib
import io
import json
import re
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
QID = re.compile(r"\d{4}_AZUL_D\d_Q\d+")
SCALES = (2.5, 2.0, 3.0, 3.5, 4.0)
PAD = 1.0


def load_pdfs():
    out = {}
    for f in glob.glob(str(ROOT / "data/enem-pdfs/oficiais/*-regular-*-azul.pdf")):
        m = re.search(r"(\d{4})-regular-(d\d)-azul", f)
        out[(int(m[1]), m[2].upper())] = f
    return out


def load_candidates():
    cands = {}

    def walk(o, qid=None):
        if isinstance(o, dict):
            i = o.get("id") or o.get("id_unico_sistema")
            if isinstance(i, str) and QID.fullmatch(i):
                qid = i
            for k, v in o.items():
                if k in ("regions", "support_render", "render") and qid:
                    cands.setdefault(qid, []).append(v)
                walk(v, qid)
        elif isinstance(o, list):
            for v in o:
                walk(v, qid)

    for f in sorted(glob.glob(str(ROOT / "data/audit/batch-*-review.json"))):
        walk(json.loads(Path(f).read_text(encoding="utf-8")))
    return cands


def regions_of(c):
    if isinstance(c, dict) and "regions" in c:
        return c["regions"], c.get("scale")
    if isinstance(c, dict):
        return [c], c.get("scale")
    if isinstance(c, list):
        return c, None
    return [], None


def find_box(cands, qid, w, h):
    for c in cands.get(qid, []):
        regs, sc = regions_of(c)
        for rg in regs:
            if not isinstance(rg, dict) or "bbox" not in rg or "page" not in rg:
                continue
            b = rg["bbox"]
            for scale in ([sc] if sc else []) + list(SCALES):
                if abs((b[2] - b[0]) * scale - w) <= 2 and abs((b[3] - b[1]) * scale - h) <= 2:
                    return rg["page"], list(b), scale
    return None


HEADER = re.compile(r"^\s*QUEST[ÃA]O\s*\d+", re.I)


def extend(page, b, skip_headers=False):
    """Estende y0/y1 para conter por inteiro linhas de texto cruzadas pela borda."""
    x0, y0, x1, y1 = b
    lines = []
    for blk in page.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            lx0, ly0, lx1, ly1 = ln["bbox"]
            ov = min(lx1, x1) - max(lx0, x0)
            if skip_headers and HEADER.match("".join(sp["text"] for sp in ln["spans"])):
                continue
            if lx1 > lx0 and ov / (lx1 - lx0) >= 0.5:
                lines.append((ly0, ly1))
    ny0, ny1 = y0, y1
    for ly0, ly1 in lines:
        if ly0 < y1 + 1.5 and ly1 > y1 - 0.5:
            ny1 = max(ny1, ly1 + PAD)
        if ly1 > y0 - 1.5 and ly0 < y0 + 0.5:
            ny0 = min(ny0, ly0 - PAD)
    return [x0, ny0, x1, ny1]


def render(page, box, scale):
    pm = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=pymupdf.Rect(*box), alpha=False)
    return Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triage", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--changes", default=str(ROOT / "data/audit/image-corrections.json"))
    args = ap.parse_args()

    results = json.loads(Path(args.triage).read_text(encoding="utf-8"))["results"]
    pdfs, cands = load_pdfs(), load_candidates()
    changes, skipped = [], []
    for ref, v in sorted(results.items()):
        if not any(f.startswith("CLIP") for f in v["flags"]):
            continue
        qid = v["questions"][0]
        path = ROOT / "data/extracted" / ref[len("/images/"):]
        old = Image.open(path).convert("RGB")
        w, h = old.size
        m = re.match(r"(\d{4})_AZUL_(D\d)", qid)
        pdf = pdfs.get((int(m[1]), m[2]))
        hit = find_box(cands, qid, w, h)
        if not pdf or not hit:
            skipped.append((qid, ref, "sem página/caixa registrada"))
            continue
        pg, box, scale = hit
        doc = pymupdf.open(pdf)
        page = doc[pg - 1]
        base = render(page, box, scale)
        if base.size != old.size or np.abs(np.asarray(base, int) - np.asarray(old, int)).max() > 8:
            skipped.append((qid, ref, "render base não reproduz o recorte antigo"))
            continue
        nb = extend(page, box)
        if nb == box:
            skipped.append((qid, ref, "nenhuma linha cruzada pela borda"))
            continue
        new = render(page, nb, scale)
        top = round((box[1] - nb[1]) * scale)
        # o miolo antigo deve estar contido sem alteração no novo recorte
        core = np.asarray(new, int)[top:top + h, :, :]
        if core.shape != np.asarray(old).shape or np.abs(core - np.asarray(old, int)).max() > 8:
            skipped.append((qid, ref, "miolo diverge após extensão"))
            continue
        buf = io.BytesIO()
        new.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
        rec = {
            "id": qid, "image": ref, "pdf": Path(pdf).name, "page": pg, "scale": scale,
            "bbox_before": box, "bbox_after": [round(x, 3) for x in nb],
            "size_before": [w, h], "size_after": list(new.size),
            "sha256_before": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sha256_after": hashlib.sha256(data).hexdigest(),
        }
        changes.append(rec)
        print(f"{qid:20} {w}x{h} -> {new.size[0]}x{new.size[1]}  {Path(ref).name}")
        if args.apply:
            path.write_bytes(data)

    print(f"\ncorrigíveis: {len(changes)} | pulados: {len(skipped)}")
    for s in skipped:
        print("  pulado", *s)
    if args.apply:
        Path(args.changes).write_text(json.dumps({"schema_version": 1, "corrections": changes},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
        print("registro:", args.changes)


if __name__ == "__main__":
    main()
