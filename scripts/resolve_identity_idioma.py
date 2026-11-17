#!/usr/bin/env python3
"""Resolve o CO_ITEM das posições 1–5 de LC (idioma) já publicadas, a partir do ITENS_PROVA oficial.

As linhas de idioma do ITENS_PROVA trazem duas variantes por posição (TP_LINGUA 0 = inglês, 1 = espanhol,
confirmado pelo gabarito oficial: nas posições em que as respostas diferem, a letra da variante 0 é a do
gabarito em inglês). O idioma da questão publicada NÃO é inferido do texto: vem da região do PDF oficial
(manifesto, conferida visualmente no lote 08) e é conferido aqui pela seção do caderno em que a região está
("Questões de 01 a 05 (opção inglês|espanhol)").

Só é aceito quando concordam: (1) o idioma do manifesto e a seção do PDF, (2) a resposta do ITENS_PROVA da
variante de idioma, (3) a letra do gabarito oficial desse idioma e (4) o gabarito publicado. Usa o CO_PROVA já
escolhido para a mesma prova/área em data/audit/identity-resolution.json. Acrescenta os itens ao arquivo
(idempotente); nada em questions.jsonl é alterado.

Uso: python scripts/resolve_identity_idioma.py
"""
import csv
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_official_gabaritos import extract_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TP = {"ingles": "0", "espanhol": "1"}
# posições de idioma que ainda não estavam no catálogo: a versão em inglês (a que vale na posição) ganha identidade aqui;
# a região vem do cabeçalho da seção em inglês do PDF (primeira ocorrência de "Questão n") e é conferida pela seção
NEW_ENGLISH = {2017: [1, 2, 3, 4, 5], 2018: [4, 5], 2024: [4]}
HEADER = re.compile(r"Quest[õo]es de 0?1 a 0?5\s*\(op[çc][ãa]o:?\s+(ingl[êe]s|espanhol)\)", re.I)


def section_language(doc, region):
    """Idioma da seção em que a região está: último cabeçalho 'Questões de 01 a 05 (opção X)' na ordem de leitura
    (página, coluna esquerda antes da direita, de cima para baixo); o cabeçalho da coluna esquerda vale para a direita."""
    col = lambda x: 0 if x < 285 else 1
    target = (region["page"], col(region["bbox"][0]), region["bbox"][1] + 5)
    best = None
    for p in range(region["page"]):
        for b in doc[p].get_text("blocks"):
            for m in HEADER.finditer(b[4]):
                key = (p + 1, col(b[0]), b[1])
                if key <= target and (best is None or key > best[0]):
                    best = (key, "ingles" if m.group(1).lower().startswith("ingl") else "espanhol")
    return best[1] if best else None


def main():
    ident_path = ROOT / "data/audit/identity-resolution.json"
    ident = json.loads(ident_path.read_text())
    manifest = {e["id"]: e for e in json.loads((ROOT / "data/audit/manifest.json").read_text())["questions"]}
    release = [json.loads(l) for l in (ROOT / "data/blue-published/questions.jsonl").read_text().splitlines()]
    todo = [q for q in release if q["area_conhecimento"] == "LC" and q["dia"] == 1 and q["posicao_prova"] <= 5]
    added, problems, rows_cache, keys = {}, [], {}, {}
    for q in todo:
        uid, year, pos = q["id_unico_sistema"], q["ano"], q["posicao_prova"]
        e = manifest[uid]
        lang = e.get("language")
        if lang not in TP:
            problems.append((uid, "idioma ausente no manifesto")); continue
        ref = next((v for k, v in ident["items"].items() if k.startswith(f"{year}_AZUL_D1_") and v["area"] == "LC" and "lingua" not in v), None)
        if ref is None:
            problems.append((uid, "CO_PROVA de LC não resolvido")); continue
        co_prova = ref["co_prova"]
        if year not in rows_cache:
            rows_cache[year] = list(csv.DictReader((ROOT / f"data/audit/identity/itens-prova-{year}-azul.csv").open(encoding="utf-8"), delimiter=";"))
            keys[year] = extract_pdf(ROOT / f"data/enem-pdfs/oficiais/{year}-regular-d1-azul-gabarito.pdf")[0]
        match = [r for r in rows_cache[year] if int(r["CO_PROVA"]) == co_prova and r["SG_AREA"] == "LC"
                 and int(r["CO_POSICAO"]) == pos and r["TP_LINGUA"] == TP[lang]]
        key = keys[year].get(pos, {}).get(lang)
        with fitz.open(ROOT / f"data/enem-pdfs/oficiais/{year}-regular-d1-azul.pdf") as doc:
            sec = section_language(doc, e["regions"][0])
        if len(match) != 1:
            problems.append((uid, f"linhas oficiais={len(match)}")); continue
        r = match[0]
        if sec != lang:
            problems.append((uid, f"seção do PDF={sec} != manifesto={lang}")); continue
        if not (r["TX_GABARITO"] == key == q["gabarito_oficial"]):
            problems.append((uid, f"respostas divergem: itens={r['TX_GABARITO']} pdf={key} publicado={q['gabarito_oficial']}")); continue
        added[uid] = dict(co_item=int(r["CO_ITEM"]), co_habilidade=int(r["CO_HABILIDADE"]) if r["CO_HABILIDADE"] else None,
                          in_item_aban=int(r["IN_ITEM_ABAN"] or 0), area="LC", tx_gabarito=r["TX_GABARITO"], co_prova=co_prova,
                          official_key=key, lingua=lang)
    new_english, new_problems = {}, []
    published = {q["id_unico_sistema"] for q in release}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_exam_candidates import candidates  # noqa: E402
    for year, positions in NEW_ENGLISH.items():
        ref = next(v for k, v in ident["items"].items() if k.startswith(f"{year}_AZUL_D1_") and v["area"] == "LC" and "lingua" not in v)
        co_prova = ref["co_prova"]
        if year not in rows_cache:
            rows_cache[year] = list(csv.DictReader((ROOT / f"data/audit/identity/itens-prova-{year}-azul.csv").open(encoding="utf-8"), delimiter=";"))
            keys[year] = extract_pdf(ROOT / f"data/enem-pdfs/oficiais/{year}-regular-d1-azul-gabarito.pdf")[0]
        cand = candidates(year, 1)
        with fitz.open(ROOT / f"data/enem-pdfs/oficiais/{year}-regular-d1-azul.pdf") as doc:
            for pos in positions:
                uid = f"{year}_AZUL_D1_Q{pos:02d}"
                if uid in added:  # já publicada e resolvida no primeiro laço: reexecução idempotente
                    new_english[uid] = added[uid]; continue
                if uid in published:
                    new_problems.append((uid, "já está no catálogo sem identidade resolvida")); continue
                sec = section_language(doc, cand[pos]["regions"][0])
                match = [r for r in rows_cache[year] if int(r["CO_PROVA"]) == co_prova and r["SG_AREA"] == "LC"
                         and int(r["CO_POSICAO"]) == pos and r["TP_LINGUA"] == "0"]
                key = keys[year].get(pos, {}).get("ingles")
                if sec != "ingles" or len(match) != 1 or match[0]["TX_GABARITO"] != key:
                    new_problems.append((uid, f"seção={sec} linhas={len(match)} itens={match and match[0]['TX_GABARITO']} pdf={key}")); continue
                r = match[0]
                new_english[uid] = dict(co_item=int(r["CO_ITEM"]), co_habilidade=int(r["CO_HABILIDADE"]) if r["CO_HABILIDADE"] else None,
                                        in_item_aban=int(r["IN_ITEM_ABAN"] or 0), area="LC", tx_gabarito=r["TX_GABARITO"], co_prova=co_prova,
                                        official_key=key, lingua="ingles")
    added.update(new_english)
    ident["items"].update(added)
    ident["language_resolution"] = dict(
        method="posições 1–5 de LC: ITENS_PROVA (CO_PROVA escolhido, TP_LINGUA 0=inglês/1=espanhol) + idioma do manifesto conferido pela seção do PDF + gabarito do idioma",
        resolved=len(added) - len(new_english),
        published_with_wrong_co_item=sum(1 for q in todo if q["id_unico_sistema"] in added and q["co_item"] != added[q["id_unico_sistema"]]["co_item"]),
        unresolved=[dict(id=u, motivo=m) for u, m in problems],
        unpublished_english=dict(resolved=sorted(new_english), unresolved=[dict(id=u, motivo=m) for u, m in new_problems]))
    ident_path.write_text(json.dumps(ident, ensure_ascii=False, indent=1) + "\n")
    print(len(added), "resolvidas;", len(problems) + len(new_problems), "pendentes")
    for u, m in problems + new_problems:
        print(" ", u, m)


if __name__ == "__main__":
    main()
