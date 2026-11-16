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
from extract_exam_candidates import candidates, raw_lines, clean  # noqa: E402
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


UNSAFE_OPT = re.compile(r"[A-Za-z]\d|\d[A-Za-z]|×|\^|=|[<>]|[\u2070-\u209f\u00b2\u00b3\u00b9]|\b[A-Z]\s[A-Z]\b")


def safe_alternativas(alts, flags):
    """Questões com fórmulas (sobrescritos e índices): a camada de texto achata expoentes e índices ('x2', '16o', 'C C 4 2'),
    e as alternativas aparecem como cartões na tela. Se algum texto for suspeito, as cinco ficam com o texto de apoio padrão
    (o recorte original mostra as alternativas corretas)."""
    if any(f.startswith("sobrescrito_ou_indice") for f in flags) and any(UNSAFE_OPT.search(t) for t in alts.values()):
        return {k: f"Alternativa {k}: reprodução gráfica oficial." for k in "ABCDE"}, True
    return alts, False


def replay_png(pdf, renders):
    """PNG gerado exatamente como o replay (documento novo + store_shrink antes do primeiro render), para que o hash bata:
    o cache de imagens do MuPDF faz o mesmo recorte variar de um processo/estado para outro."""
    from PIL import Image
    with fitz.open(pdf) as document:
        fitz.TOOLS.store_shrink(100)
        panels = []
        for r in renders:
            sc = r["scale"]
            pix = document[r["page"] - 1].get_pixmap(matrix=fitz.Matrix(sc, sc), clip=fitz.Rect(r["bbox"]), alpha=False)
            panels.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples).crop(tuple(r["pixel_trim"])))
    img = Image.new("RGB", (max(p.width for p in panels), sum(p.height for p in panels)), "white")
    top = 0
    for p in panels:
        img.paste(p, (0, top)); top += p.height
    buf = BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue(), img.size


def content_rect(page, rect):
    """União de texto, imagens e desenhos da região (sem marcas escuras da margem e sem a barra do cabeçalho)."""
    boxes = []
    for blk in page.get_text("dict", clip=rect)["blocks"]:
        if blk.get("type") == 0:
            for ln in blk["lines"]:
                if "".join(s["text"] for s in ln["spans"]).strip():
                    boxes.append(fitz.Rect(ln["bbox"]))
    pw = page.rect.width
    for i in page.get_image_info():
        r = fitz.Rect(i["bbox"])
        if r.width < 40 and (r.x1 <= 30 or r.x0 >= pw - 30 or r.height > 600):
            continue  # faixa decorativa da margem da página (2024)
        if r.intersects(rect):
            boxes.append(r & rect)
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if not (r.intersects(rect) and r.width > 3 and r.height > 3) or (r.width > 200 and r.height < 16):
            continue
        if r.x1 <= 24 or r.x0 >= pw - 24:
            continue  # desenho dentro da faixa da margem
        f = d.get("fill")
        if f and all(0.28 <= c <= 0.33 for c in f) and (r.width < 35 or r.height < 35) and (r.x0 < 25 or r.x1 > page.rect.width - 25 or r.x0 < 0):
            continue  # marca escura da margem da página
        pr = page.rect
        if f and r.width < 60 and (r.x0 < pr.x0 or r.y0 < pr.y0 or r.x1 > pr.x1 or r.y1 > pr.y1):
            continue  # marca preenchida que sai da página (aba de margem)
        if r.x0 >= rect.x0 + 1 and r.width < 500:
            boxes.append(r & rect)
    if not boxes:
        return rect
    u = boxes[0]
    for b in boxes[1:]:
        u |= b
    return fitz.Rect(u.x0 - PAD, u.y0 - PAD, u.x1 + PAD, u.y1 + PAD) & rect


MARK = re.compile(r"^([A-E])(?:[\s\t]+\S.{0,14})?$")


def graphic_content(doc, regions, number):
    """Conteúdo de questões cujas alternativas são gráficas ou não saem como texto: o comando vem das linhas antes
    da primeira letra da sequência A–E (mesma coluna), e as alternativas recebem o texto de apoio padrão.
    Reprova (ValueError) se as cinco letras A–E não aparecerem em sequência na mesma coluna."""
    lines = []
    for reg in regions:
        page = doc[reg["page"] - 1]
        for t, x, z in raw_lines(page, fitz.Rect(reg["bbox"])):
            if t.strip():
                lines.append((clean(t.strip()), x))
    head = next((i for i, (t, _) in enumerate(lines[:3]) if HEADER.match(t)), None)
    if head is not None:
        lines = lines[head + 1:]  # descarta ruído antes do cabeçalho "Questão n"
    best = None
    for col in sorted({round(x / 8) for _, x in lines}):
        seq = [(i, MARK.match(t).group(1)) for i, (t, x) in enumerate(lines) if round(x / 8) == col and MARK.match(t)]
        for start in range(len(seq)):
            want, idx = "A", []
            for i, letter in seq[start:]:
                if letter == want:
                    idx.append(i); want = chr(ord(want) + 1)
                    if want == "F":
                        break
            if len(idx) == 5:
                best = best or idx
                break
        if best:
            break
    if not best:
        raise ValueError("letras A–E não encontradas em sequência na mesma coluna")
    stem = " ".join(t for t, _ in lines[:best[0]]).strip()
    stem = re.sub(r"\s+", " ", stem)
    if not stem:
        raise ValueError("comando vazio")
    return dict(enunciado=stem, texto_base="", alternativas={k: f"Alternativa {k}: reprodução gráfica oficial." for k in "ABCDE"})


def trim_to_header(page, crop, number):
    """Corta a caixa entre o fim da tinta da linha anterior (linha base + descendente) e o início da tinta do cabeçalho
    'Questão n' quando o fim da questão anterior fica colado nele (as caixas das linhas se sobrepõem).
    Devolve (caixa, ok); ok é False quando a tinta das duas linhas se sobrepõe."""
    lines = []
    for blk in page.get_text("dict", clip=crop + (0, -30, 0, 0))["blocks"]:
        for ln in blk.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                sp = ln["spans"][0]
                lines.append((ln["bbox"], sp["origin"][1], sp["size"], t))
    head = next(((b, o, z) for b, o, z, t in lines if (m := HEADER.match(t)) and int(m.group(1)) == number and b[1] > crop.y0 - 5), None)
    if head is None:
        return crop, True
    hb, ho, hz = head
    prev = [(b, o, z) for b, o, z, t in lines if b[1] < hb[1] and b[3] > hb[1] - 1.0 and not HEADER.match(t)]
    if not prev:
        return crop, True
    prev_ink = max(o + 0.28 * z for b, o, z in prev)
    head_ink = ho - 0.78 * hz
    if prev_ink >= head_ink:
        return crop, False
    return fitz.Rect(crop.x0, max(crop.y0, (prev_ink + head_ink) / 2), crop.x1, crop.y1), True


def _lines(page, window):
    out = []
    for blk in page.get_text("dict", clip=window)["blocks"]:
        for ln in blk.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                sp = max(ln["spans"], key=lambda q: q["size"])
                out.append((fitz.Rect(ln["bbox"]), ln["spans"][0]["origin"][1], sp["size"], t))
    return out


def extend_cut_lines(page, crop, number):
    """Estende a caixa na vertical até conter a tinta (linha base + descendente) das linhas que a borda corta, sem entrar
    na tinta do cabeçalho de outra questão (corta no meio do vão entre elas)."""
    for _ in range(3):
        lines = _lines(page, crop + (-3, -3, 3, 40))
        heads = [(b, o, z) for b, o, z, t in lines if (m := HEADER.match(t)) and int(m.group(1)) != number]
        for b, o, z, t in lines:
            if b.height >= 40 or HEADER.match(t):
                continue
            ink_bottom, ink_top = o + 0.28 * z, o - 0.78 * z
            if o <= crop.y1 + 1 and ink_bottom > crop.y1 + 0.3:  # corta a base
                target = ink_bottom + 0.8
                below = [hb for hb, ho, hz in heads if hb.y0 > o - 2]
                if below:
                    head_ink = min(ho - 0.78 * hz for hb, ho, hz in heads if hb.y0 > o - 2)
                    if ink_bottom >= head_ink:
                        continue
                    target = min(target, (ink_bottom + head_ink) / 2)
                crop = fitz.Rect(crop.x0, crop.y0, crop.x1, max(crop.y1, target))
            if o >= crop.y0 - 1 and ink_top < crop.y0 - 0.3:  # corta o topo
                crop = fitz.Rect(crop.x0, ink_top - 0.8, crop.x1, crop.y1)
    return crop


def gates(page, crop, number):
    """Linhas de texto cortadas (pela tinta) e cabeçalhos de outras questões dentro do recorte."""
    problems = []
    for b, o, z, t in _lines(page, crop + (-3, -3, 3, 3)):
        if b.height >= 40:
            continue
        m = HEADER.match(t)
        if m and int(m.group(1)) != number:
            problems.append("cabeçalho de outra questão: " + t)
            continue
        if o <= crop.y1 + 1 and o + 0.28 * z > crop.y1 + 0.3 and o > crop.y0:
            problems.append("linha cortada na borda inferior: " + t[:30])
        if o >= crop.y0 - 1 and o - 0.78 * z < crop.y0 - 0.3 and o < crop.y1 and not HEADER.match(t):
            problems.append("linha cortada na borda superior: " + t[:30])
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
        ex = dict(exams[(year, day)])
        if "source_sha256" not in ex:  # 2024 D1: o inventário não traz as fontes; usa as já auditadas no manifesto de publicação
            ref = next(e for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]
                       if e["year"] == year and e["day"] == day and e.get("application") == "regular")
            ex.update(source_url=ref["source_url"], source_sha256=ref["source_sha256"],
                      answer_key_url=ref["answer_source_url"], answer_key_sha256=ref["answer_source_sha256"])
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
            assert c["regions"], uid
            assert r["tx_gabarito"] == c["answer"] == r["official_key"], f"identidade não corroborada: {uid}"
            src = c["content"]
            if not (src and len(src["alternativas"]) == 5):
                try:
                    src = graphic_content(doc, c["regions"], n)
                except ValueError as e:
                    failures.append((uid, [str(e)])); continue
            alts, replaced = safe_alternativas(src["alternativas"], c["flags"])
            src = dict(src, alternativas=alts)
            fix = TEXT_OVERRIDES.get(uid, {})
            enun = fix.get("enunciado", src["enunciado"])
            base_text = (src["texto_base"] or "") + fix.get("texto_base_append", "")
            if any(STRANGE.search(v) for v in [enun, base_text, *src["alternativas"].values()]):
                failures.append((uid, ["glifo privado no texto"])); continue
            provisional = dict(enunciado=enun, texto_base=base_text,
                               alternativas=src["alternativas"],
                               metadados_visual=dict(contem_imagem=False, descricao_imagem=None, caminho_local_imagem=None))
            pending = dict(id_unico_sistema=uid, co_item=r["co_item"], ano=year, dia=day, cor_prova="AZUL", posicao_prova=n,
                           area_conhecimento=r["area"], gabarito_oficial=None, co_habilidade=r["co_habilidade"],
                           in_item_aban=r["in_item_aban"], conteudo=provisional, parametros_tri=None,
                           preview_status="REVIEW_TEXT", preview_unverified=True, scoring_enabled=False,
                           preview_warning="Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação.")
            from PIL import Image
            fitz.TOOLS.store_shrink(100)  # igual ao replay: o cache de imagens do MuPDF pode mudar o primeiro render
            texts, renders, panels, bad_all = [], [], [], []
            for k, reg in enumerate(c["regions"]):
                page = doc[reg["page"] - 1]
                rect = fitz.Rect(reg["bbox"])
                crop = content_rect(page, rect)
                if k == 0:
                    crop, ok_trim = trim_to_header(page, crop, n)
                    if not ok_trim:
                        bad_all.append("tinta da linha anterior sobreposta ao cabeçalho")
                crop = extend_cut_lines(page, crop, n)
                bad_all += gates(page, crop, n)
                texts.append(page.get_text(clip=rect))
                pm = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=crop, alpha=False)
                renders.append(dict(page=reg["page"], bbox=[round(v, 3) for v in crop], scale=SCALE, pixel_trim=[0, 0, pm.width, pm.height]))
                panels.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))
            if bad_all:
                failures.append((uid, bad_all)); continue
            text = "\n".join(texts)
            data, size = replay_png(pdf, renders)
            image = f"/images/verified/batch{batch}-{year}-azul-d{day}-q{n:03d}-source.png"
            content = dict(provisional, metadados_visual=dict(contem_imagem=True, descricao_imagem=DESCRIPTION, caminho_local_imagem=image))
            q = dict(pending, conteudo=content, gabarito_oficial=c["answer"])
            digest = record_digest(q)
            results.append(dict(
                id=uid, year=year, day=day, number=n, application="regular", language=None,
                regions=[dict(page=g["page"], bbox=g["bbox"], is_prefix=False) for g in c["regions"]],
                pending_row=pending, before_content=provisional, official_answer=c["answer"], source=source,
                source_file=pdf.name, key_file=key.name, source_text=text, source_text_sha256=sha_bytes(text.encode()),
                status="APPROVED", classification="RECOVERABLE",
                decision="Recorte original da região da questão (texto, figuras, comando e alternativas), gabarito oficial e identidade resolvida; região conferida em folha de contato.",
                after_content=content, record_sha256=digest,
                presentation_metadata=dict(mode="composition", includes_command=True, source=image, source_sha256=sha_bytes(data),
                                           evidence=f"data/audit/batch-{batch}-review.json", record_sha256=digest),
                assets=dict(source=dict(image=image, sha256=sha_bytes(data), render=renders, width=size[0], height=size[1])),
                visual_review=dict.fromkeys(["text", "options", "graphics", "credits", "continuity", "answer"], True),
                identity_reconciliation=dict(
                    method="official ITENS_PROVA: the azul CO_PROVA whose answer sequence equals the official key (data/audit/identity-resolution.json)",
                    co_item=r["co_item"], co_prova=r["co_prova"], tx_gabarito=r["tx_gabarito"], official_answer=c["answer"],
                    independent_item_csv="official Inep ITENS_PROVA (see data/audit/identity/sources.json)",
                    note="CO_ITEM não vem do fused (CO_PROVA azul diferente do caderno do PDF)."),
                parser_flags=c["flags"], manual_text_overrides=sorted(fix) or None, options_replaced_by_placeholder=replaced))
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
