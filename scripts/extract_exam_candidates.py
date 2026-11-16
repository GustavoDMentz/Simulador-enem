#!/usr/bin/env python3
"""Extrai candidatos de questões direto do PDF oficial (camada de texto) + gabarito oficial.

Não aprova nada e não grava no catálogo. Para cada posição devolve regiões
(página/caixa), texto estruturado (base, comando, alternativas A–E), gabarito
oficial, sinais de risco e uma classificação:

  tier_a  texto puro: 5 alternativas, sem figuras/desenhos/sobrescritos/poesia/
          numeração de linhas/hifenização — candidato a conferência visual leve
  tier_b  precisa de revisão manual (figura, fórmula, poesia, continuação etc.)

Por quê: o campo `gabarito_oficial` dos fused discorda do gabarito oficial em
cerca de metade das posições não auditadas; só o gabarito do PDF oficial é usado.

Uso:
  python scripts/extract_exam_candidates.py --year 2025 --day 1 --out cand.json
Requer PyMuPDF e pdftotext (poppler). Os PDFs vêm de data/enem-pdfs/oficiais.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_official_gabaritos import extract_pdf  # noqa: E402
from segment_question_candidates import find_headers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# (ano, dia, questão) -> índices das regiões que realmente pertencem à questão (conferido na imagem)
REGION_KEEP = {
    (2021, 1, 45): [0], (2021, 2, 118): [0], (2021, 2, 120): [0], (2021, 2, 138): [0], (2021, 2, 161): [0],
    # contracapa (logo) e faixa de cabeçalho da página ("Exame Nacional do Ensino Médio") detectadas como continuação
    (2022, 2, 180): [0], (2025, 2, 108): [0], (2025, 2, 119): [0], (2025, 2, 127): [0], (2025, 2, 130): [0], (2025, 2, 135): [0, 2],  # 135: região 2 = coluna das alternativas (EXTRA_REGION)
    # questão que ocupa a página inteira: a "continuação" é a mesma página relida desde o topo (região duplicada)
    (2017, 2, 121): [0], (2017, 2, 152): [0], (2018, 2, 159): [0], (2018, 2, 173): [0], (2019, 2, 139): [0],
    (2022, 2, 95): [0], (2022, 2, 156): [0], (2023, 2, 132): [0], (2024, 2, 161): [0], (2024, 2, 168): [0],
    (2025, 2, 138): [0], (2025, 2, 169): [0],
    # a página repete a questão vizinha acima ou abaixo: só a primeira região é da questão
    (2018, 2, 126): [0],
    (2024, 2, 180): [0],  # a continuação é o logo "enem" da contracapa
    (2020, 1, 58): [0],  # a faixa de 15 pt no topo da outra coluna é só o resto da questão vizinha
}
# (ano, dia, questão) -> x0 da região de continuação: ela vem numa faixa de largura total que traz o fim da questão vizinha
# na coluna esquerda; só a coluna direita é continuação (conferido na imagem)
CONT_X0 = {(2025, 1, 16): 283.46, (2025, 1, 44): 283.46, (2025, 1, 50): 283.46, (2025, 1, 67): 283.46}
# (ano, dia, questão) -> regiões acrescentadas (página 0-based, x0, y0, x1, y1): alternativas na coluna direita da mesma página
EXTRA_REGION = {(2025, 2, 135): [(14, 283.46, 57.0, 567.0, 740.0)]}
# questões cujas letras A–E vêm com espaços em vez de tabulação (A com um espaço, E com um espaço…): normaliza para "X\t"
SPACE_OPT = {(2020, 1, 38), (2020, 1, 57), (2020, 1, 58)}


def tab_options(lines):
    """Troca por tabulação as letras A–E em sequência (a última ocorrência de 'A' em diante) separadas só por espaços."""
    pat = re.compile(r"^([A-E])\s+(?=\S)")
    idx = [i for i, (t, *_) in enumerate(lines) if pat.match(t)]
    starts = [i for i in idx if lines[i][0][0] == "A"]
    if not starts:
        return lines
    out, want = list(lines), "A"
    for i in idx:
        if i < starts[-1] or lines[i][0][0] != want:
            continue
        t, *rest = lines[i]
        out[i] = (pat.sub(want + "\t", t, count=1), *rest)
        want = chr(ord(want) + 1)
    return out


# a região invade o banner da seção seguinte ("LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS / Questões de 01 a 05 (opção espanhol)")
BANNER_CUT = {(2017, 1, 5), (2018, 1, 5)}
# texto compartilhado ("Texto para as Questões de 06 a 10") que precede as questões: (ano, dia, questão) -> (página 0-based, x0, y0, x1, y1)
SHARED_PREFIX = {(2025, 1, n): (5, 0.0, 70.0, 567.0, 740.0) for n in range(6, 11)}

TOP, BOTTOM = 57.0, 740.0
OPT = re.compile(r"^([A-E])\s*\t(.*)$")
OPT2 = re.compile(r"^([A-E])\s{2,}(\S.*)$")  # PDFs em que a letra vem separada por espaços, sem tabulação
DEIXIS = re.compile(r"\b(texto|trecho|fragmento|figura|imagem|gr[aá]fico|tabela|charge|tirinha|poema|mapa|quadro|"
                    r"infogr[aá]fico|fotografia|can[cç][aã]o|letra|an[uú]ncio|cartaz|pintura|obra|cena|ilustra[cç][aã]o)\b", re.I)
CREDIT = re.compile(r"(Dispon[ií]vel em|Acesso em|\(adaptad[oa]\)|\(fragmento\)|Fonte:|Dispon[ií]vel em:)", re.I)


def reading_headers(doc):
    out = []
    for pi, page in enumerate(doc):
        mid = page.rect.width / 2
        for h in find_headers(page):
            x0, y0 = h["bbox"][0], h["bbox"][1]
            out.append(dict(n=h["number"], page=pi, y=y0, x=x0, col="L" if x0 < mid else "R"))
    return out


def col_clip(page, col, y0, y1):
    W, mid = page.rect.width, page.rect.width / 2
    x0, x1 = (0, mid) if col == "L" else (mid, W)
    # página de coluna única: alguma linha de texto cruza a linha central
    for blk in page.get_text("dict", clip=fitz.Rect(0, y0, W, y1))["blocks"]:
        for ln in blk.get("lines", []):
            a, b = ln["bbox"][0], ln["bbox"][2]
            if a < mid - 25 and b > mid + 25:
                return fitz.Rect(0, y0, W, y1)
    return fitz.Rect(x0, y0, x1, y1)


def region_for(doc, heads, h):
    page = doc[h["page"]]
    below = [x["y"] for x in heads if x["page"] == h["page"] and x["col"] == h["col"] and x["y"] > h["y"] + 1]
    # na página de coluna única o próximo cabeçalho pode estar em "L" e "R": usa qualquer um abaixo
    anyb = [x["y"] for x in heads if x["page"] == h["page"] and x["y"] > h["y"] + 1]
    full = col_clip(page, h["col"], h["y"] - 1.5, BOTTOM)
    if full.width > page.rect.width * 0.7:
        below = anyb
    end = min(below) - 1.5 if below else BOTTOM
    return h["page"], col_clip(page, h["col"], h["y"] - 1.5, end), not below


def continuation(doc, heads, h):
    """Região seguinte (topo da próxima coluna/página) até o primeiro cabeçalho."""
    page_i, col = h["page"], h["col"]
    if col == "L":
        nxt_page, nxt_col = page_i, "R"
    else:
        nxt_page, nxt_col = page_i + 1, "L"
    if nxt_page >= len(doc):
        return None
    page = doc[nxt_page]
    first = [x["y"] for x in heads if x["page"] == nxt_page and x["col"] == nxt_col]
    end = (min(first) - 1.5) if first else BOTTOM
    if end - TOP < 8:
        return None
    return nxt_page, col_clip(page, nxt_col, TOP, end)


def graphics_in(page, rect):
    """Conta imagens e desenhos relevantes; ignora réguas do cabeçalho e moldura da página."""
    imgs = 0
    for im in page.get_image_info():
        r = fitz.Rect(im["bbox"]) & rect
        if not r.is_empty and r.height >= 8 and r.width >= 8:
            imgs += 1
    draws = 0
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if r.width > page.rect.width * 0.9 and r.height > page.rect.height * 0.9:
            continue  # moldura de sangria da página
        if (r.height < 6 and r.width > 60) or (r.width < 6 and r.height > 60):
            continue  # réguas e fios de coluna
        if r.width <= 12 and r.height <= 12:
            continue  # marcador gráfico da letra da alternativa (2019)
        if r.height <= 22 and r.width > 60 and rect.y0 - 2 <= r.y0 <= rect.y0 + 22:
            continue  # barra do cabeçalho "QUESTÃO N" (2019)
        if r.intersects(rect):
            draws += 1
    return imgs, draws


def sup_sub(page, rect):
    n = 0
    for blk in page.get_text("dict", clip=rect)["blocks"]:
        for ln in blk.get("lines", []):
            sizes = [s["size"] for s in ln["spans"] if s["text"].strip()]
            for s in ln["spans"]:
                if s["text"].strip() and (s["flags"] & 1 or (sizes and s["size"] < 0.8 * max(sizes))):
                    n += 1
    return n


def raw_lines(page, rect):
    """Linhas de texto (texto, x0) na ordem de leitura da região."""
    out = []
    for blk in page.get_text("dict", clip=rect, sort=True)["blocks"]:
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            text = "".join(sp["text"] for sp in ln["spans"]).replace("\xa0", " ").rstrip()
            size = max((sp["size"] for sp in ln["spans"] if sp["text"].strip()), default=0.0)
            if size < 4:
                continue  # marca d'água repetida em corpo minúsculo ("ENEM 2022 ENEM 2022 ...")
            out.append((text, ln["bbox"][0], size))
    return out


LIG = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"}
STRANGE = re.compile("[\ue000-\uf8ff\ufffd\x00-\x08\x0b-\x1f]")


def clean(t):
    for k, v in LIG.items():
        t = t.replace(k, v)
    return t


def paragraphs(lines):
    """Junta linhas em parágrafos.

    Linhas coladas à margem continuam o parágrafo; recuo de 5–30 pt após fim de frase abre
    parágrafo novo; linhas muito recuadas (créditos, títulos centralizados) formam grupos próprios.
    """
    items = [(clean(t.strip()), x, z) for t, x, z in lines if t.strip()]
    if not items:
        return ""
    left = min(x for _, x, _ in items)
    zs = sorted(z for _, _, z in items if z)
    body = zs[len(zs) // 2] if zs else 0
    kind = lambda x, z: "far" if (x > left + 30 or (body and z <= 0.88 * body)) else ("ind" if x > left + 5 else "flush")
    head = lambda t: re.fullmatch(r"TEXTO\s+[IVX]+", t) is not None
    paras, cur, prev, pk = [], [], "", None
    for t, x, z in items:
        k = kind(x, z)
        new = (not cur or head(t) or head(prev) or (k == "far" and pk != "far") or (pk == "far" and k != "far")
               or (k == "ind" and re.search(r"[.!?:”\"\]\)…]$", prev) is not None))
        if new and cur:
            paras.append(" ".join(cur))
            cur = []
        cur.append(t)
        prev, pk = t, k
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(re.sub(r"\s+", " ", p).strip() for p in paras)


def parse(lines_all):
    """Divide em (base, comando, alternativas). Devolve (dict, flags)."""
    flags = []
    pairs = [(t, x, z) for t, x, z in lines_all if t.strip()]
    if pairs and re.fullmatch(r"\s*Quest[ãa]o\s+\d+\s*", pairs[0][0], re.I):
        pairs = pairs[1:]
    # alguns PDFs desenham a letra da alternativa como linha própria antes de "A\t texto"
    pairs = [p for i, p in enumerate(pairs)
             if not (re.fullmatch(r"[A-E]", p[0].strip()) and i + 1 < len(pairs) and pairs[i + 1][0].startswith(p[0].strip() + "\t"))]
    lines = [t for t, *_ in pairs]
    opt_re = OPT
    first_opt = next((i for i, ln in enumerate(lines) if OPT.match(ln)), None)
    if first_opt is None:
        first_opt = next((i for i, ln in enumerate(lines) if OPT2.match(ln)), None)
        opt_re = OPT2
    if first_opt is None:
        return None, ["sem_alternativas"]
    stem, opts = lines[:first_opt], {}
    stem_pairs = pairs[:first_opt]
    if any(STRANGE.search(t) or any(c in t for c in LIG) for t in lines):
        flags.append("caractere_estranho_ou_ligadura")
    cur = None
    for ln in lines[first_opt:]:
        m = opt_re.match(ln)
        if m and m.group(1) not in opts and (cur is None or ord(m.group(1)) == ord(cur) + 1):
            cur = m.group(1)
            opts[cur] = m.group(2).strip()
        elif cur:
            opts[cur] = (opts[cur] + " " + ln.strip()).strip()
    if "".join(opts) != "ABCDE":
        return None, ["alternativas_incompletas:" + "".join(opts)]
    if any(not v for v in opts.values()):
        flags.append("alternativa_vazia")
    # base x comando: o comando começa após a última linha de crédito; senão, última frase
    sizes = sorted(z for _, _, z in stem_pairs if z)
    body = sizes[len(sizes) // 2] if sizes else 0
    small = [i for i, (_, _, z) in enumerate(stem_pairs) if body and z <= 0.88 * body]
    # crédito = última linha de fonte menor (a fonte do comando é a do corpo do texto)
    last_credit = max(small) if small else max((i for i, ln in enumerate(stem) if CREDIT.search(ln)), default=None)
    if last_credit is not None and last_credit < len(stem) - 1:
        base_text = paragraphs(stem_pairs[:last_credit + 1])
        cmd_text = paragraphs(stem_pairs[last_credit + 1:])
        base_lines, cmd_lines = [base_text], [cmd_text]
    else:
        text = " ".join(s.strip() for s in stem)
        cut = max(text.rfind(". ", 0, len(text) - 1), -1)
        base_lines = [paragraphs(stem_pairs)[:0] or text[:cut + 1]] if cut > 0 else []
        cmd_lines = [text[cut + 2:]] if cut > 0 else [text]
        flags.append("comando_por_ultima_frase")
    join = lambda ls: "\n\n".join(l for l in ls if l).strip()
    base, cmd = join(base_lines), re.sub(r"\s+", " ", join(cmd_lines)).strip()
    opts = {k: clean(re.sub(r"\s+", " ", v)).strip() for k, v in opts.items()}
    if any(s.rstrip().endswith("-") for s in stem + list(opts.values())):
        flags.append("hifen_fim_de_linha")
    if sum(1 for s in stem if re.fullmatch(r"\s*\d{1,3}\s*", s)):
        flags.append("numeracao_de_linhas")
    short = [len(s) for s in stem if s.strip()]
    if len(short) > 6 and sum(short) / len(short) < 38:
        flags.append("possivel_poesia")
    if not cmd:
        flags.append("sem_comando")
    if not base and DEIXIS.search(cmd):
        flags.append("sem_base_mas_refere_apoio")
    elif not base and len(cmd) < 110:
        flags.append("sem_base_comando_curto")
    return dict(texto_base=base or None, enunciado=cmd, alternativas=opts), flags


def shared_ranges(doc):
    """Intervalos de questões que compartilham um texto ("Texto para as Questões de 06 a 10")."""
    out = []
    for page in doc:
        for m in re.finditer(r"Textos?\s+para\s+as\s+Quest[õo]es\s+de\s+(\d+)\s+a\s+(\d+)", page.get_text(), re.I):
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def candidates(year, day):
    base = ROOT / "data/enem-pdfs/oficiais"
    doc = fitz.open(base / f"{year}-regular-d{day}-azul.pdf")
    keys, ambiguous, _ = extract_pdf(base / f"{year}-regular-d{day}-azul-gabarito.pdf")
    heads = reading_headers(doc)
    shared = shared_ranges(doc)
    out = {}
    for h in sorted(heads, key=lambda x: (x["n"], x["page"], x["y"])):
        n = h["n"]
        if n in out:
            out[n]["flags"].append("cabecalho_duplicado")
            continue
        page_i, rect, open_end = region_for(doc, heads, h)
        regions = [(page_i, rect, False)]
        lines = raw_lines(doc[page_i], rect)
        if (year, day, n) in SPACE_OPT:
            lines = tab_options(lines)
        content, flags = parse(lines)
        if content is None and open_end:
            cont = continuation(doc, heads, h)
            if cont:
                regions.append((cont[0], cont[1], True))
                lines = lines + raw_lines(doc[cont[0]], cont[1])
                content, flags = parse(lines)
        if (year, day, n) in CONT_X0 and len(regions) > 1:
            pg, r, flag = regions[1]
            regions[1] = (pg, fitz.Rect(CONT_X0[(year, day, n)], r.y0, r.x1, r.y1), flag)
            lines = sum((raw_lines(doc[pg_], r_) for pg_, r_, _ in regions), [])
            content, flags = parse(lines)
        if (year, day, n) in EXTRA_REGION:
            for pg, x0, y0, x1, y1 in EXTRA_REGION[(year, day, n)]:
                regions.append((pg, fitz.Rect(x0, y0, x1, y1), True))
            lines = sum((raw_lines(doc[pg_], r_) for pg_, r_, _ in regions), [])
            content, flags = parse(lines)
        if (year, day, n) in REGION_KEEP:  # a continuação detectada é outra coisa (ex.: instruções da redação)
            regions = [regions[i] for i in REGION_KEEP[(year, day, n)]]
            flags = [f for f in flags if f != "continua_em_outra_coluna_ou_pagina"]
        if (year, day, n) in BANNER_CUT:
            cut = []
            for pi, r, pref in regions:
                for b in doc[pi].get_text("blocks", clip=r):
                    if "LINGUAGENS, CÓDIGOS" in b[4] and b[1] > r.y0 + 20:
                        r = fitz.Rect(r.x0, r.y0, r.x1, b[1] - 2)
                        break
                cut.append((pi, r, pref))
            regions = cut
        if (year, day, n) in SHARED_PREFIX:
            pg, x0, y0, x1, y1 = SHARED_PREFIX[(year, day, n)]
            regions.insert(0, (pg, fitz.Rect(x0, y0, x1, y1), True))
        imgs = draws = sups = 0
        for pi, r, _ in regions:
            a, b = graphics_in(doc[pi], r)
            imgs += a
            draws += b
            sups += sup_sub(doc[pi], r)
        key = keys.get(n)
        ans = None
        if key and "comum" in key:
            ans = key["comum"]
        elif key:
            flags.append("gabarito_por_idioma")
        else:
            flags.append("sem_gabarito")
        if n in ambiguous:
            flags.append("gabarito_ambiguo")
        if imgs:
            flags.append(f"imagens:{imgs}")
        if draws:
            flags.append(f"desenhos:{draws}")
        if sups:
            flags.append(f"sobrescrito_ou_indice:{sups}")
        if len(regions) > 1:
            flags.append("continua_em_outra_coluna_ou_pagina")
        if n <= 5:
            flags.append("idioma_ingles_espanhol")
        if any(a <= n <= b for a, b in shared):
            flags.append("texto_compartilhado")
        hard = [f for f in flags if not f.startswith("comando_por_ultima_frase")]
        out[n] = dict(
            number=n, shared_prefix=((year, day, n) in SHARED_PREFIX), answer=ans, answer_by_language=(key if key and "comum" not in key else None), content=content, flags=flags,
            regions=[dict(page=pi + 1, bbox=[round(v, 2) for v in r], is_prefix=pref) for pi, r, pref in regions],
            tier="tier_a" if content and ans and not hard else "tier_b",
        )
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    res = candidates(args.year, args.day)
    Path(args.out).write_text(json.dumps({"year": args.year, "day": args.day, "candidates": res},
                                         ensure_ascii=False, indent=1), encoding="utf-8")
    tiers = {}
    for c in res.values():
        tiers[c["tier"]] = tiers.get(c["tier"], 0) + 1
    print(len(res), "posições;", tiers)


if __name__ == "__main__":
    main()
