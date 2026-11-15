#!/usr/bin/env python3
"""Corrige recortes do lote 08 que cortam texto na borda ou trazem fragmentos
da página vizinha (cabeçalho/marca d'água "enem 20xx").

Os ativos do lote 08 registram `render` (página, bbox, escala, pixel_trim) e o
SHA-256 do PNG. Aqui:
  1. se uma linha de texto é cruzada pela borda superior/inferior do recorte,
     estende-o em pixels inteiros (mesma grade de pixels, miolo idêntico);
  2. senão, se há um fragmento de tinta colado na borda inferior/superior,
     separado do conteúdo por uma faixa em branco, apara o fragmento.
Depois atualiza `render`, largura/altura e SHA-256 em batch-08-review.json e
confere que `apply_enem_batch_08.render_asset` reproduz o PNG gravado.

Uso: python scripts/fix_clipped_crops_batch08.py --triage triage.json [--apply]
"""
import argparse
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_clipped_crops import ROOT, PAD, extend, furniture, load_pdfs  # noqa: E402

REPORT = ROOT / "data/audit/batch-08-review.json"
INK = 200


def walk_assets(o, out):
    if isinstance(o, dict):
        if "image" in o and "render" in o and "sha256" in o:
            out[o["image"]] = o
        for v in o.values():
            walk_assets(v, out)
    elif isinstance(o, list):
        for v in o:
            walk_assets(v, out)


def render_panels(doc, asset):
    pymupdf.TOOLS.store_shrink(100)
    panels = []
    for r in asset["render"]:
        s = r["scale"]
        pix = doc[r["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(s, s), clip=pymupdf.Rect(r["bbox"]), alpha=False)
        panel = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        panels.append(panel.crop(tuple(r["pixel_trim"])))
    img = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)), "white")
    top = 0
    for p in panels:
        img.paste(p, (0, top))
        top += p.height
    return img


def to_png(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def try_extend(doc, asset):
    """Estende topo do 1º painel / base do último painel por pixels inteiros."""
    new = json.loads(json.dumps(asset["render"]))
    changed = False
    for idx, side in ((0, "top"), (len(new) - 1, "bottom")):
        r = new[idx]
        s = r["scale"]
        x0, y0, x1, y1 = r["bbox"]
        tx0, ty0, tx1, ty1 = r["pixel_trim"]
        page = doc[r["page"] - 1]
        cur = [x0 + tx0 / s, y0 + ty0 / s, x0 + tx1 / s, y0 + ty1 / s]
        ext = extend(page, cur, skip_headers=True)
        kt = max(0, math.ceil((cur[1] - ext[1]) * s - 1e-6)) if side == "top" else 0
        kb = max(0, math.ceil((ext[3] - cur[3]) * s - 1e-6)) if side == "bottom" else 0
        if kt or kb:
            r["bbox"] = [x0, y0 - kt / s, x1, y1 + kb / s]
            r["pixel_trim"] = [tx0, ty0, tx1, ty1 + kt + kb]
            changed = True
    return new if changed else None


def has_text(doc, r, y0px, y1px):
    """Há linha de texto do PDF na faixa vertical [y0px, y1px) do painel?"""
    s = r["scale"]
    x0, by0, x1, _ = r["bbox"]
    a, b = by0 + y0px / s, by0 + y1px / s
    for blk in doc[r["page"] - 1].get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            lx0, ly0, lx1, ly1 = ln["bbox"]
            ov = min(lx1, x1) - max(lx0, x0)
            if lx1 > lx0 and ov / (lx1 - lx0) >= 0.5 and ly0 < b and ly1 > a and "".join(sp["text"] for sp in ln["spans"]).strip() \
                    and not furniture("".join(sp["text"] for sp in ln["spans"]), ly0):
                return True
    return False


def try_trim(doc, asset, old):
    """Apara fragmento de tinta colado na base (ou topo), após faixa em branco."""
    g = np.asarray(old.convert("L"))
    rows = (g < INK).any(axis=1)
    h = len(rows)
    new = json.loads(json.dumps(asset["render"]))
    changed = False
    # base
    if rows[-1]:
        j = h - 1
        while j >= 0 and rows[j]:
            j -= 1
        frag = h - 1 - j
        k = j
        while k >= 0 and not rows[k]:
            k -= 1
        gap = j - k
        if k >= 0 and frag <= 40 and gap >= 6:
            cut = h - (k + 1 + 6)  # mantém 6 px de respiro
            r = new[-1]
            if has_text(doc, r, r["pixel_trim"][3] - cut, r["pixel_trim"][3]):
                return None
            r["pixel_trim"][3] -= cut
            changed = True
    # topo
    if rows[0]:
        j = 0
        while j < h and rows[j]:
            j += 1
        frag = j
        k = j
        while k < h and not rows[k]:
            k += 1
        gap = k - j
        if k < h and frag <= 40 and gap >= 6:
            cut = k - 6
            r = new[0]
            if has_text(doc, r, r["pixel_trim"][1], r["pixel_trim"][1] + cut):
                return None
            r["pixel_trim"][1] += cut
            changed = True
    return new if changed else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triage", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--changes", default=str(ROOT / "data/audit/image-corrections.json"))
    args = ap.parse_args()

    triage = json.loads(Path(args.triage).read_text(encoding="utf-8"))["results"]
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assets = {}
    walk_assets(report["results"], assets)
    pdfs = load_pdfs()
    changes, skipped = [], []
    for ref, v in sorted(triage.items()):
        flags = [f for f in v["flags"] if f in ("CLIP_TOP", "CLIP_BOTTOM")]
        if not flags or ref not in assets:
            continue
        qid, asset = v["questions"][0], assets[ref]
        m = re.match(r"(\d{4})_AZUL_(D\d)", qid)
        doc = pymupdf.open(pdfs[(int(m[1]), m[2])])
        path = ROOT / "data/extracted" / ref[len("/images/"):]
        old = Image.open(path).convert("RGB")
        try:
            base = render_panels(doc, asset)
        except (IndexError, ValueError):
            skipped.append((qid, ref, "PDF local não corresponde à aplicação do recorte"))
            continue
        exact = sha(to_png(base)) == asset["sha256"] and to_png(base) == path.read_bytes()
        if not exact:
            # versões diferentes do MuPDF reamostram imagens com ±1 em alguns pixels;
            # só aceitamos aparar (subimagem exata do PNG publicado), nunca re-renderizar.
            near = base.size == old.size and np.abs(np.asarray(base, int) - np.asarray(old, int)).max() <= 2
            if not near or len(asset["render"]) != 1:
                skipped.append((qid, ref, "render original não reproduz o PNG publicado"))
                continue
        how, new_render = "trim", try_trim(doc, asset, old)
        if not new_render:
            how, new_render = "extend", try_extend(doc, asset)
        if not new_render:
            skipped.append((qid, ref, "sem linha cortada nem fragmento isolável"))
            continue
        new_asset = dict(asset, render=new_render)
        if exact:
            img = render_panels(doc, new_asset)
        elif how == "trim":
            o, n = asset["render"][0]["pixel_trim"], new_render[0]["pixel_trim"]
            img = old.crop((0, n[1] - o[1], old.width, old.height - (o[3] - n[3])))
        else:
            skipped.append((qid, ref, "render original não reproduz o PNG; extensão exigiria re-renderizar"))
            continue
        data = to_png(img)
        if how == "extend":
            # o PNG antigo deve estar contido sem alteração no novo
            kt = new_render[0]["pixel_trim"][1] - asset["render"][0]["pixel_trim"][1]
            ow, oh = old.size
            top = round((asset["render"][0]["bbox"][1] - new_render[0]["bbox"][1]) * asset["render"][0]["scale"]) if len(new_render) == 1 else 0
            if len(new_render) == 1:
                core = np.asarray(img, int)[top:top + oh, :ow]
                if core.shape != np.asarray(old).shape or np.abs(core - np.asarray(old, int)).max() > 0:
                    skipped.append((qid, ref, "miolo diverge após extensão"))
                    continue
        else:
            oa, na = np.asarray(old, int), np.asarray(img, int)
            ok = any(np.array_equal(oa[a:a + na.shape[0]], na) for a in range(0, oa.shape[0] - na.shape[0] + 1))
            if not ok:
                skipped.append((qid, ref, "recorte aparado não é subimagem do antigo"))
                continue
        rec = {"id": qid, "image": ref, "method": how, "pdf": Path(pdfs[(int(m[1]), m[2])]).name,
               "render_before": asset["render"], "render_after": new_render,
               "size_before": list(old.size), "size_after": list(img.size),
               "sha256_before": asset["sha256"], "sha256_after": sha(data)}
        changes.append((rec, data, path, asset, new_render, img.size))
        print(f"{qid:20} {how:6} {old.size[0]}x{old.size[1]} -> {img.size[0]}x{img.size[1]}  {Path(ref).name}")

    print(f"\ncorrigíveis: {len(changes)} | pulados: {len(skipped)}")
    for s in skipped:
        print("  pulado", *s)
    if not args.apply:
        return
    for rec, data, path, asset, new_render, size in changes:
        path.write_bytes(data)
        asset["render"], asset["width"], asset["height"], asset["sha256"] = new_render, size[0], size[1], rec["sha256_after"]
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cf = Path(args.changes)
    doc = json.loads(cf.read_text(encoding="utf-8"))
    doc["corrections"] += [c[0] for c in changes]
    cf.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in ("data/audit/manifest.json", "data/audit/question-presentation.json", "data/audit/batch-08-review.json"):
        p = ROOT / f
        t = p.read_text(encoding="utf-8")
        for c in changes:
            t = t.replace(c[0]["sha256_before"], c[0]["sha256_after"])
        p.write_text(t, encoding="utf-8")
    print("aplicado.")


if __name__ == "__main__":
    main()
