#!/usr/bin/env python3
"""Gera data/audit/batch-09-review.json a partir do PDF oficial (camada de texto) e do gabarito oficial.

Seleção do lote 09 (fixa, revisada visualmente região a região em folhas de contato):
texto puro, 5 alternativas A–E, sem figuras/desenhos/sobrescritos, uma única região,
e a resposta do fused coincidindo com o gabarito oficial (corroboração de identidade).
O gabarito usado é sempre o do PDF oficial. Nada aqui altera o catálogo; isso é feito por
apply_enem_batch_09.py, que repete cada verificação contra os PDFs originais.

Uso: python scripts/build_enem_batch_09_report.py --pdf-root data/enem-pdfs/oficiais
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_exam_candidates import candidates  # noqa: E402
from publish_blue_candidates import record_digest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BATCH = "09"
SELECTION = {
    (2018, 1): [23, 33, 68, 70, 72, 76, 79, 85, 89],
    (2018, 2): [97, 101, 102, 134, 175, 178],
    (2022, 1): [28, 29, 31, 34, 36, 85],
    (2022, 2): [92, 97, 122, 123, 127, 132, 151],
    (2023, 1): [39, 42, 45, 81, 82, 83, 85, 87, 90],
    (2023, 2): [101, 104, 106, 122, 130],
    (2025, 1): [12, 25, 27, 40, 52, 54, 55, 58, 65, 70, 71, 73, 78, 79, 82, 85, 88],
    (2025, 2): [102, 141, 150, 155, 171],  # Q95 (poema com versos) fica fora: exige quebras de linha
}
BASE = "4fa28cd536ab9c3a4281f5b4eb964e5aa8bab6d0+pr27"  # main + PR #27 (recortes corrigidos)
SCALE = 2.5
PAD = 6.0
DESCRIPTION = "Recorte original da prova oficial (texto, comando e alternativas) para conferência. Abra para ampliar."


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tight_rect(page, rect):
    """Caixa do texto da região + folga, nunca maior que a região."""
    boxes = []
    for blk in page.get_text("dict", clip=rect)["blocks"]:
        for ln in blk.get("lines", []):
            if "".join(s["text"] for s in ln["spans"]).strip():
                boxes.append(fitz.Rect(ln["bbox"]))
    u = boxes[0]
    for b in boxes[1:]:
        u |= b
    u = fitz.Rect(u.x0 - PAD, u.y0 - PAD, u.x1 + PAD, u.y1 + PAD) & rect
    return u


def render_png(doc, render):
    fitz.TOOLS.store_shrink(100)
    page = doc[render["page"] - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(render["scale"], render["scale"]), clip=fitz.Rect(render["bbox"]), alpha=False)
    from PIL import Image
    from io import BytesIO
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).crop(tuple(render["pixel_trim"]))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img.size


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf-root", type=Path, default=ROOT / "data/enem-pdfs/oficiais")
    ap.add_argument("--out", type=Path, default=ROOT / "data/audit/batch-09-review.json")
    args = ap.parse_args()

    exams = {(int(e["year"]), int(e["day"])): e for e in json.loads((ROOT / "data/enem-pdfs/manifest.json").read_text())["exams"]
             if e["application"] == "regular" and e["color"] == "azul"}
    snapshot = {q["id_unico_sistema"]: q for q in map(json.loads, (ROOT / "data/audit/session-recovery/preview-questions.jsonl").read_text().splitlines())}
    manifest_ids = {e["id"] for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]}
    results, sources = [], []
    for (year, day), numbers in SELECTION.items():
        ex = exams[(year, day)]
        pdf = args.pdf_root / f"{year}-regular-d{day}-azul.pdf"
        key = args.pdf_root / f"{year}-regular-d{day}-azul-gabarito.pdf"
        assert sha_bytes(pdf.read_bytes()) == ex["source_sha256"], pdf
        assert sha_bytes(key.read_bytes()) == ex["answer_key_sha256"], key
        source = dict(year=year, day=day, source_url=ex["source_url"], source_sha256=ex["source_sha256"],
                      answer_source_url=ex["answer_key_url"], answer_source_sha256=ex["answer_key_sha256"])
        sources.append(dict(source, source_file=pdf.name, key_file=key.name))
        cand = candidates(year, day)
        fused = {r["posicao_prova"]: r for r in map(json.loads, (ROOT / f"data/fused/questoes_enem_{year}_AZUL_D{day}.jsonl").read_text().splitlines())}
        doc = fitz.open(pdf)
        for n in numbers:
            uid = f"{year}_AZUL_D{day}_Q{n:02d}"
            assert uid not in manifest_ids, uid
            c, f = cand[n], fused[n]
            assert c["tier"] == "tier_a" and len(c["regions"]) == 1, uid
            assert f["gabarito_oficial"] == c["answer"], f"identidade não corroborada: {uid}"
            pending = {**{k: f[k] for k in ("id_unico_sistema", "co_item", "ano", "dia", "cor_prova", "posicao_prova",
                                           "area_conhecimento")},
                       "gabarito_oficial": None, "co_habilidade": f["co_habilidade"], "in_item_aban": f["in_item_aban"],
                       "conteudo": f["conteudo"], "parametros_tri": None, "preview_status": "REVIEW_TEXT",
                       "preview_unverified": True, "scoring_enabled": False,
                       "preview_warning": "Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação."}
            reg = c["regions"][0]
            page = doc[reg["page"] - 1]
            rect = fitz.Rect(reg["bbox"])
            text = page.get_text(clip=rect)
            tr = tight_rect(page, rect)
            tmp = dict(page=reg["page"], bbox=[round(v, 3) for v in tr], scale=SCALE, pixel_trim=[0, 0, 10 ** 5, 10 ** 5])
            pm = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=fitz.Rect(tmp["bbox"]), alpha=False)
            tmp["pixel_trim"] = [0, 0, pm.width, pm.height]
            data, size = render_png(doc, tmp)
            image = f"/images/verified/batch{BATCH}-{year}-azul-d{day}-q{n:03d}-source.png"
            content = dict(enunciado=c["content"]["enunciado"], texto_base=c["content"]["texto_base"] or "",
                           alternativas=c["content"]["alternativas"],
                           metadados_visual=dict(contem_imagem=True, descricao_imagem=DESCRIPTION, caminho_local_imagem=image))
            q = dict(pending, conteudo=content, gabarito_oficial=c["answer"])
            digest = record_digest(q)
            results.append(dict(
                id=uid, year=year, day=day, number=n, application="regular", language=None,
                regions=[dict(page=reg["page"], bbox=reg["bbox"], is_prefix=False)],
                pending_row=pending, before_content=f["conteudo"], official_answer=c["answer"], source=source,
                source_file=pdf.name, key_file=key.name, source_text=text, source_text_sha256=sha_bytes(text.encode()),
                status="APPROVED", classification="RECOVERABLE",
                decision="Texto da camada oficial do PDF, cinco alternativas, créditos e gabarito oficial; região conferida visualmente sem figuras e sem continuação.",
                after_content=content, record_sha256=digest,
                presentation_metadata=dict(mode="text", source=image, source_sha256=sha_bytes(data),
                                           evidence=f"data/audit/batch-{BATCH}-review.json", record_sha256=digest),
                assets=dict(source=dict(image=image, sha256=sha_bytes(data), render=[tmp], width=size[0], height=size[1])),
                visual_review=dict.fromkeys(["text", "options", "graphics", "credits", "continuity", "answer"], True),
                identity_reconciliation=dict(
                    method="fused identity corroborated by the official answer key at the same position",
                    fused_answer=f["gabarito_oficial"], official_answer=c["answer"], co_item=f["co_item"],
                    independent_item_csv="unavailable; no claim of independent CO_ITEM revalidation",
                    note="Posições cuja resposta no fused diverge do gabarito oficial não entram neste lote."),
                parser_flags=c["flags"]))
    release_path = ROOT / "data/blue-published/questions.jsonl"
    lines = release_path.read_bytes().splitlines(keepends=True)
    prev = {json.loads(l)["id_unico_sistema"]: l for l in lines}
    done = {r["id"] for r in results}
    assert not done & set(prev), "o lote 09 só adiciona identificadores novos"
    report = dict(schema_version=1, batch=BATCH, base_commit=BASE, examined=len(results), approved_before=len(prev),
                  newly_approved=len(results), approved_after=len(prev) + len(results),
                  previous_catalog_sha256=sha_bytes(b"".join(lines)),
                  previous_lines_sha256={uid: sha_bytes(l) for uid, l in prev.items()},
                  sources=sources, results=results,
                  limitations=["Sem revalidação independente de CO_ITEM (ITENS_PROVA indisponível).",
                               "Parâmetros TRI permanecem nulos; nenhum cálculo de TRI.",
                               "Texto vindo da camada de texto do PDF; a conferência visual foi feita por folhas de contato das regiões."])
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(results), "questões →", args.out)


if __name__ == "__main__":
    main()
