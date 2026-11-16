#!/usr/bin/env python3
"""Gera data/audit/batch-NN-review.json para lotes de questões COM FIGURA (recorte original do PDF oficial).

Cada questão do lote é uma região única do caderno azul regular (cabeçalho "QUESTÃO n" até o fim da coluna), com
cinco alternativas A–E em texto, cuja identidade foi resolvida pelo ITENS_PROVA oficial. O aluno vê o recorte
original (apresentação `composition`, com o comando e as alternativas dentro da imagem); o texto da camada do PDF
fica como apoio (inclui rótulos das figuras). A caixa do recorte é a união de texto, imagens e desenhos da região,
sem as marcas escuras da margem da página. Gates automáticos por questão: nenhuma linha de texto cortada pela borda
do recorte, nenhum cabeçalho de outra questão dentro dele, resposta do ITENS_PROVA = gabarito do PDF.
A seleção está em data/audit/figure-batches/batch-NN-selection.json e foi conferida em folhas de contato.

Uso: python scripts/build_enem_figure_batch_report.py --batch 14 [--pdf-root data/enem-pdfs/oficiais]
"""
import argparse
import hashlib
import json
import re
import sys
from io import BytesIO
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_exam_candidates import candidates  # noqa: E402
from publish_blue_candidates import record_digest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCALE = 2.5
PAD = 6.0
DESCRIPTION = "Recorte original da prova oficial (texto, figuras, comando e alternativas) para conferência. Abra para ampliar."
STRANGE = re.compile("[\ue000-\uf8ff\ufffd\x00-\x08\x0b-\x1f]")
# Correções de texto conferidas na imagem do recorte, onde a camada de texto do PDF traz glifos privados de fórmulas
# (o texto é lido por leitores de tela quando a questão é exibida como recorte). id -> campos substituídos.
TEXT_OVERRIDES = {
    "2018_AZUL_D2_Q136": dict(
        enunciado="Com base nessas informações, o banco que transferiu a maior quantia via TED é o banco",
        texto_base_append=" Esta é a matriz obtida para essa análise: a matriz A é apresentada na imagem."),
    "2018_AZUL_D2_Q152": dict(enunciado="Esse conjunto é dado pelos pares ordenados (x ; y) ∈ ℕ × ℕ, tais que"),
}
HEADER = re.compile(r"^\s*Quest[ãa]o\s+(\d+)\s*$", re.I)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def content_rect(page, rect):
    """União de texto, imagens e desenhos da região (sem marcas escuras da margem e sem a barra do cabeçalho)."""
    boxes = []
    for blk in page.get_text("dict", clip=rect)["blocks"]:
        if blk.get("type") == 0:
            for ln in blk["lines"]:
                if "".join(s["text"] for s in ln["spans"]).strip():
                    boxes.append(fitz.Rect(ln["bbox"]))
        elif blk.get("type") == 1:
            boxes.append(fitz.Rect(blk["bbox"]))
    for i in page.get_image_info():
        r = fitz.Rect(i["bbox"])
        if r.intersects(rect):
            boxes.append(r & rect)
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if not (r.intersects(rect) and r.width > 3 and r.height > 3) or (r.width > 200 and r.height < 16):
            continue
        f = d.get("fill")
        if f and all(0.28 <= c <= 0.33 for c in f) and (r.width < 35 or r.height < 35) and (r.x0 < 25 or r.x1 > page.rect.width - 25 or r.x0 < 0):
            continue  # marca escura da margem da página
        pr = page.rect
        if f and r.width < 60 and (r.x0 < pr.x0 or r.y0 < pr.y0 or r.x1 > pr.x1 or r.y1 > pr.y1):
            continue  # marca preenchida que sai da página (aba de margem)
        if r.x0 >= rect.x0 + 1 and r.width < 500:
            boxes.append(r & rect)
    u = boxes[0]
    for b in boxes[1:]:
        u |= b
    return fitz.Rect(u.x0 - PAD, u.y0 - PAD, u.x1 + PAD, u.y1 + PAD) & rect


def extend_cut_lines(page, crop, number):
    """Estende a caixa na vertical até conter por inteiro as linhas que a borda corta (sem entrar no cabeçalho de outra questão)."""
    heads = []
    for blk in page.get_text("dict", clip=crop + (0, -40, 0, 40))["blocks"]:
        for ln in blk.get("lines", []):
            m = HEADER.match("".join(s["text"] for s in ln["spans"]).strip())
            if m and int(m.group(1)) != number:
                heads.append(ln["bbox"][1])
    for _ in range(3):
        for blk in page.get_text("dict", clip=crop + (-3, -3, 3, 3))["blocks"]:
            for ln in blk.get("lines", []):
                if not "".join(s["text"] for s in ln["spans"]).strip():
                    continue
                r = fitz.Rect(ln["bbox"])
                inside = max(0.0, min(r.y1, crop.y1) - max(r.y0, crop.y0))
                if r.height < 40 and 0.1 * r.height < inside < 0.9 * r.height:
                    if r.y1 > crop.y1:
                        below = [h for h in heads if h > crop.y1 - 1]
                        crop = fitz.Rect(crop.x0, crop.y0, crop.x1, min(r.y1, (min(below) - 0.1) if below else r.y1))
                    if r.y0 < crop.y0:
                        crop = fitz.Rect(crop.x0, r.y0, crop.x1, crop.y1)
    return crop


def gates(page, crop, number):
    """Linhas de texto cortadas pela borda e cabeçalhos de outras questões dentro do recorte."""
    problems = []
    for blk in page.get_text("dict", clip=crop + (-3, -3, 3, 3))["blocks"]:
        for ln in blk.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if not t:
                continue
            r = fitz.Rect(ln["bbox"])
            inside = max(0.0, min(r.y1, crop.y1) - max(r.y0, crop.y0))
            if r.height < 40 and 0.1 * r.height < inside < 0.9 * r.height:
                problems.append("linha cortada na borda vertical: " + t[:30])
            m = HEADER.match(t)
            if m and int(m.group(1)) != number:
                problems.append("cabeçalho de outra questão: " + t)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--pdf-root", type=Path, default=ROOT / "data/enem-pdfs/oficiais")
    args = ap.parse_args()
    batch = args.batch
    selection = {tuple(map(int, k.split("-"))): v for k, v in json.loads((ROOT / f"data/audit/figure-batches/batch-{batch}-selection.json").read_text()).items()}
    out_path = ROOT / f"data/audit/batch-{batch}-review.json"
    exams = {(int(e["year"]), int(e["day"])): e for e in json.loads((ROOT / "data/enem-pdfs/manifest.json").read_text())["exams"]
             if e["application"] == "regular" and e["color"] == "azul"}
    ident = json.loads((ROOT / "data/audit/identity-resolution.json").read_text())["items"]
    manifest_ids = {e["id"] for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]}
    results, sources, failures = [], [], []
    for (year, day), numbers in sorted(selection.items()):
        ex = exams[(year, day)]
        pdf = args.pdf_root / f"{year}-regular-d{day}-azul.pdf"
        key = args.pdf_root / f"{year}-regular-d{day}-azul-gabarito.pdf"
        assert sha_bytes(pdf.read_bytes()) == ex["source_sha256"], pdf
        assert sha_bytes(key.read_bytes()) == ex["answer_key_sha256"], key
        source = dict(year=year, day=day, source_url=ex["source_url"], source_sha256=ex["source_sha256"],
                      answer_source_url=ex["answer_key_url"], answer_source_sha256=ex["answer_key_sha256"])
        sources.append(dict(source, source_file=pdf.name, key_file=key.name))
        cand = candidates(year, day)
        doc = fitz.open(pdf)
        for n in numbers:
            uid = f"{year}_AZUL_D{day}_Q{n:02d}"
            assert uid not in manifest_ids, uid
            c, r = cand[n], ident[uid]
            assert len(c["regions"]) == 1 and c["content"] and len(c["content"]["alternativas"]) == 5, uid
            assert r["tx_gabarito"] == c["answer"] == r["official_key"], f"identidade não corroborada: {uid}"
            reg = c["regions"][0]
            page = doc[reg["page"] - 1]
            rect = fitz.Rect(reg["bbox"])
            crop = extend_cut_lines(page, content_rect(page, rect), n)
            bad = gates(page, crop, n)
            if bad:
                failures.append((uid, bad)); continue
            fix = TEXT_OVERRIDES.get(uid, {})
            enun = fix.get("enunciado", c["content"]["enunciado"])
            base_text = (c["content"]["texto_base"] or "") + fix.get("texto_base_append", "")
            assert not any(STRANGE.search(v) for v in [enun, base_text, *c["content"]["alternativas"].values()]), "glifo privado no texto: " + uid
            provisional = dict(enunciado=enun, texto_base=base_text,
                               alternativas=c["content"]["alternativas"],
                               metadados_visual=dict(contem_imagem=False, descricao_imagem=None, caminho_local_imagem=None))
            pending = dict(id_unico_sistema=uid, co_item=r["co_item"], ano=year, dia=day, cor_prova="AZUL", posicao_prova=n,
                           area_conhecimento=r["area"], gabarito_oficial=None, co_habilidade=r["co_habilidade"],
                           in_item_aban=r["in_item_aban"], conteudo=provisional, parametros_tri=None,
                           preview_status="REVIEW_TEXT", preview_unverified=True, scoring_enabled=False,
                           preview_warning="Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação.")
            text = page.get_text(clip=rect)
            pm = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=crop, alpha=False)
            render = dict(page=reg["page"], bbox=[round(v, 3) for v in crop], scale=SCALE, pixel_trim=[0, 0, pm.width, pm.height])
            from PIL import Image
            fitz.TOOLS.store_shrink(100)
            img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
            buf = BytesIO(); img.save(buf, format="PNG"); data = buf.getvalue()
            image = f"/images/verified/batch{batch}-{year}-azul-d{day}-q{n:03d}-source.png"
            content = dict(provisional, metadados_visual=dict(contem_imagem=True, descricao_imagem=DESCRIPTION, caminho_local_imagem=image))
            q = dict(pending, conteudo=content, gabarito_oficial=c["answer"])
            digest = record_digest(q)
            results.append(dict(
                id=uid, year=year, day=day, number=n, application="regular", language=None,
                regions=[dict(page=reg["page"], bbox=reg["bbox"], is_prefix=False)],
                pending_row=pending, before_content=provisional, official_answer=c["answer"], source=source,
                source_file=pdf.name, key_file=key.name, source_text=text, source_text_sha256=sha_bytes(text.encode()),
                status="APPROVED", classification="RECOVERABLE",
                decision="Recorte original da região da questão (texto, figuras, comando e alternativas), gabarito oficial e identidade resolvida; região conferida em folha de contato.",
                after_content=content, record_sha256=digest,
                presentation_metadata=dict(mode="composition", includes_command=True, source=image, source_sha256=sha_bytes(data),
                                           evidence=f"data/audit/batch-{batch}-review.json", record_sha256=digest),
                assets=dict(source=dict(image=image, sha256=sha_bytes(data), render=[render], width=img.size[0], height=img.size[1])),
                visual_review=dict.fromkeys(["text", "options", "graphics", "credits", "continuity", "answer"], True),
                identity_reconciliation=dict(
                    method="official ITENS_PROVA: the azul CO_PROVA whose answer sequence equals the official key (data/audit/identity-resolution.json)",
                    co_item=r["co_item"], co_prova=r["co_prova"], tx_gabarito=r["tx_gabarito"], official_answer=c["answer"],
                    independent_item_csv="official Inep ITENS_PROVA (see data/audit/identity/sources.json)",
                    note="CO_ITEM não vem do fused (CO_PROVA azul diferente do caderno do PDF)."),
                parser_flags=c["flags"], manual_text_overrides=sorted(fix) or None))
    release_path = ROOT / "data/blue-published/questions.jsonl"
    lines = release_path.read_bytes().splitlines(keepends=True)
    prev = {json.loads(l)["id_unico_sistema"]: l for l in lines}
    assert not {r["id"] for r in results} & set(prev), "o lote só adiciona identificadores novos"
    report = dict(schema_version=1, batch=batch, examined=len(results), approved_before=len(prev), newly_approved=len(results),
                  approved_after=len(prev) + len(results), previous_catalog_sha256=sha_bytes(b"".join(lines)),
                  previous_lines_sha256={uid: sha_bytes(l) for uid, l in prev.items()}, sources=sources, results=results,
                  gate_failures=[dict(id=u, problemas=p) for u, p in failures],
                  limitations=["Questões com figura: o aluno vê o recorte original do PDF; o texto de apoio vem da camada de texto e inclui rótulos das figuras.",
                               "Parâmetros TRI permanecem nulos no registro; o carregador junta o TRI oficial pelo CO_ITEM resolvido.",
                               "A conferência visual foi feita por folhas de contato das regiões, não pixel a pixel."])
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(len(results), "questões →", out_path, "| gates reprovados:", len(failures))
    for u, p in failures:
        print(" ", u, p)


if __name__ == "__main__":
    main()
