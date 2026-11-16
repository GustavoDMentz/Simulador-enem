#!/usr/bin/env python3
"""Recupera o texto das questões de 2021 cuja camada de texto do caderno AZUL está corrompida.

O PDF azul de 2021 (D1 e D2) traz fontes com mapeamento de caracteres quebrado: o recorte visual
é perfeito, mas parte das linhas do texto extraído vira lixo. Os outros cadernos do mesmo dia
(rosa, amarelo, branco, cinza) têm as mesmas questões em outra ordem e a corrupção cai em linhas
diferentes. Para cada questão pendente:

  1. o CO_ITEM da posição azul vem de data/audit/identity-resolution.json;
  2. o mesmo CO_ITEM é procurado nos outros cadernos (ITENS_PROVA oficial; a ordem do caderno é
     conferida contra o gabarito oficial PDF daquela cor) e a questão é extraída com as mesmas regras;
  3. linha a linha, usa-se a primeira versão sem lixo (azul primeiro). Um caderno só vale se tiver o
     mesmo número de linhas e coincidir nas linhas limpas de ambos;
  4. as linhas que sobram corrompidas viram o marcador ⟦?⟧ e só são preenchidas por transcrição
     manual conferida na imagem (data/audit/text-recovery-2021-fills.json).

Uso:
  python scripts/recover_2021_text.py --itens ITENS_PROVA_2021.csv --pdf-dir DIR_DOS_CADERNOS \
      --out data/audit/text-recovery-2021.json
"""
import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_exam_candidates as ex  # noqa: E402
import resolve_identity as ri  # noqa: E402
from audit_official_gabaritos import extract_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://download.inep.gov.br/enem/provas_e_gabaritos/"
# (cor, dia) -> código do caderno no nome do arquivo do Inep; CO_PROVA por área (série regular do ITENS_PROVA)
CADERNOS = {
    ("rosa", 1): "D1_CD4", ("rosa", 2): "D2_CD8", ("amarela", 1): "D1_CD2", ("amarela", 2): "D2_CD5",
    ("branca", 1): "D1_CD3", ("cinza", 2): "D2_CD6",
}
CO_PROVA = {
    "rosa": {"LC": "891", "CH": "882", "CN": "912", "MT": "901"},
    "amarela": {"LC": "890", "CH": "880", "CN": "910", "MT": "900"},
    "branca": {"LC": "892", "CH": "881"},
    "cinza": {"CN": "911", "MT": "902"},
}
BAD = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\ue000-\uf8ff\ufffd]|[\[\]]\$|\$[\[\]]|[a-zà-ú]4$")  # inclui controles C1, símbolos soltos e o ponto final lido como "4" pela fonte quebrada
ALT_BAD = re.compile(r"^([A-E])[ \t]{1,2}(?=[\x00-\x1f])")  # letra da alternativa seguida de lixo
GAP = "⟦?⟧"
# alternativas gráficas em duas colunas (A, B, C à esquerda e D, E à direita): as letras não formam sequência na mesma coluna.
# uid -> número de linhas do enunciado depois do cabeçalho (a última é o comando); as alternativas viram o texto de apoio padrão.
GRAPHIC_STEM = {"2021_AZUL_D2_Q161": 6}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines_of(doc, regions):
    out = []
    for r in regions:
        out += [(t, x, z) for t, x, z in ex.raw_lines(doc[r["page"] - 1], fitz.Rect(r["bbox"])) if t.strip()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--itens", type=Path, required=True)
    ap.add_argument("--pdf-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    ident = json.loads((ROOT / "data/audit/identity-resolution.json").read_text())["items"]
    published = {json.loads(l)["id_unico_sistema"] for l in (ROOT / "data/blue-published/questions.jsonl").open()}
    rows = list(csv.DictReader(args.itens.open(encoding="latin-1"), delimiter=";"))
    groups = collections.defaultdict(list)
    for r in rows:
        if r["SG_AREA"] == "LC" and r["TP_LINGUA"] != "":
            continue
        groups[(r["CO_PROVA"], r["SG_AREA"])].append(r)
    pos = {}
    for (p, a), rs in groups.items():
        gp = ri.global_pos(a, rs)
        for r in rs:
            pos[(p, r["CO_ITEM"])] = gp[id(r)]

    # 1) a ordem de cada caderno confere com o gabarito oficial PDF da cor
    sources, azul_doc, docs, cands = {}, {}, {}, {}
    for (cor, dia), code in CADERNOS.items():
        pdf, key_pdf = args.pdf_dir / f"2021_PV_impresso_{code}.pdf", args.pdf_dir / f"2021_GB_impresso_{code}.pdf"
        keys, _, _ = extract_pdf(key_pdf)
        ok = tot = 0
        for area, cp in CO_PROVA[cor].items():
            rs = groups[(cp, area)]
            gp = ri.global_pos(area, rs)
            for r in rs:
                k = keys.get(gp[id(r)])
                if k and "comum" in k:
                    tot += 1
                    ok += k["comum"] == r["TX_GABARITO"]
        assert tot >= 85 and ok >= tot - 1, (cor, dia, ok, tot)  # no máximo 1 anulada oficial sem letra
        sources[f"{cor}-d{dia}"] = dict(
            cor=cor, dia=dia, source_url=f"{BASE}2021_PV_impresso_{code}.pdf", source_sha256=sha(pdf),
            answer_key_url=f"{BASE}2021_GB_impresso_{code}.pdf", answer_key_sha256=sha(key_pdf),
            co_prova=CO_PROVA[cor], ordem_conferida_com_gabarito=dict(iguais=ok, comparadas=tot))
        docs[(cor, dia)] = fitz.open(pdf)
        ex.ROOT = args.pdf_dir / f"_{cor}"
        (ex.ROOT / "data/enem-pdfs/oficiais").mkdir(parents=True, exist_ok=True)
        for n, src in ((f"2021-regular-d{dia}-azul.pdf", pdf), (f"2021-regular-d{dia}-azul-gabarito.pdf", key_pdf)):
            link = ex.ROOT / "data/enem-pdfs/oficiais" / n
            if not link.exists():
                link.symlink_to(src.resolve())
        cands[(cor, dia)] = ex.candidates(2021, dia)

    ex.ROOT = ROOT
    cands[("azul", 1)], cands[("azul", 2)] = ex.candidates(2021, 1), ex.candidates(2021, 2)
    azul_docs = {d: fitz.open(ROOT / f"data/enem-pdfs/oficiais/2021-regular-d{d}-azul.pdf") for d in (1, 2)}

    fills_path = ROOT / "data/audit/text-recovery-2021-fills.json"
    fills = {k: v for k, v in json.loads(fills_path.read_text()).items() if not k.startswith("_")} if fills_path.exists() else {}

    previous = json.loads(args.out.read_text())["items"] if args.out.exists() else {}
    result = {}
    for uid, it in sorted(ident.items()):
        if not uid.startswith("2021") or "lingua" in it or (uid in published and uid not in previous):
            continue  # publicadas só entram se já estavam neste arquivo (lotes anteriores continuam reproduzíveis)
        n, day = int(uid.rsplit("Q", 1)[1]), (1 if it["area"] in ("LC", "CH") else 2)
        az = cands[("azul", day)][n]
        base = lines_of(azul_docs[day], az["regions"])
        versions, used = [("azul", [t for t, _, _ in base])], []
        for (cor, d), _ in CADERNOS.items():
            cp = CO_PROVA[cor].get(it["area"])
            if d != day or not cp:
                continue
            rp = pos.get((cp, str(it["co_item"])))
            c = cands[(cor, d)].get(rp) if rp else None
            if not c or not c["regions"]:
                continue
            other = [t for t, _, _ in lines_of(docs[(cor, d)], c["regions"])]
            if len(other) != len(base):
                continue
            if any(not BAD.search(a) and not BAD.search(b) and a != b for i, (a, b) in enumerate(zip([t for t, _, _ in base], other)) if i):
                continue  # layout divergente: não usa
            versions.append((cor, other))
            used.append(dict(cor=cor, posicao=rp, co_prova=cp))
        merged, origin = [], []
        two_spaces = any(not BAD.search(t) and ex.OPT2.match(t) for _, v in versions for t in v)
        sep = "  " if two_spaces else "\t"  # mesmo estilo das alternativas limpas (OPT2 x OPT)
        for k, (t, x, z) in enumerate(base):
            pick = next(((cor, v[k]) for cor, v in versions if not BAD.search(v[k])), None)
            if pick:
                merged.append((pick[1], x, z)); origin.append(pick[0])
            else:
                m = ALT_BAD.match(t)
                merged.append(((m.group(1) + sep + GAP) if m else GAP, x, z)); origin.append(None)
        gaps = sum(1 for o in origin if o is None)
        manual = list(fills.get(uid, []))
        if gaps and manual:
            it_fill = iter(manual)
            def fill(t):
                f = next(it_fill)
                if f.startswith("!"):  # substitui a linha inteira (ex.: rótulo "A =" de matriz lido como letra de alternativa)
                    return f[1:]
                m = re.match(r"^([A-E])\|(.*)$", f)  # linha inteira de alternativa sem a letra reconhecida
                return (m.group(1) + sep + m.group(2)) if m else t.replace(GAP, f)
            merged = [(fill(t) if GAP in t else t, x, z) for t, x, z in merged]
            assert next(it_fill, None) is None and len(manual) == gaps, f"{uid}: {gaps} lacunas, {len(manual)} transcrições"
        content, flags = ex.parse(merged)
        if content is None and uid in GRAPHIC_STEM:
            k = GRAPHIC_STEM[uid]
            stem = [t for t, _, _ in merged[1:1 + k]]
            assert not any(GAP in t for t in stem), uid
            content = dict(texto_base=" ".join(stem[:-1]) or None, enunciado=stem[-1],
                           alternativas={c: f"Alternativa {c}: reprodução gráfica oficial." for c in "ABCDE"})
            flags = flags + ["alternativas_graficas_em_duas_colunas"]
        if content is None:  # alternativas com um só espaço depois da letra ("A 1", "A kiwi."): reescreve as cinco linhas
            hits = [(i, m.group(1)) for i, (t, _, _) in enumerate(merged)
                    if not BAD.search(t) and (m := re.match(r"^([A-E])\s{1,2}(\S.*)$", t))]
            idx = {}
            for start in range(len(hits) - 1, -1, -1):  # a última letra A que seja seguida de B, C, D e E em ordem
                if hits[start][1] != "A":
                    continue
                seq, want = {}, "A"
                for i, letter in hits[start:]:
                    if letter == want:
                        seq[letter] = i
                        want = chr(ord(want) + 1)
                if len(seq) == 5:
                    idx = seq
                    break
            if len(idx) == 5:
                alt = [(f"{t[0]}  {t[1:].strip()}", x, z) if i in idx.values() else (t, x, z) for i, (t, x, z) in enumerate(merged)]
                content, flags = ex.parse(alt)
        result[uid] = dict(
            number=n, day=day, co_item=it["co_item"], lacunas=gaps, transcricao_manual=bool(gaps and manual),
            cadernos_usados=used, linhas_por_origem=dict(collections.Counter(o or "lacuna" for o in origin)),
            content=content, parse_flags=flags, text_lines=[t for t, _, _ in merged], line_x=[round(x, 1) for _, x, _ in merged])
    args.out.write_text(json.dumps(dict(
        schema_version=1,
        note=("Texto de questões de 2021 recuperado de outros cadernos pelo CO_ITEM (azul tem camada de texto corrompida). "
              "O recorte e o gabarito continuam vindo do caderno azul."),
        itens_prova=dict(sha256=sha(args.itens), url="https://download.inep.gov.br/microdados/microdados_enem_2021.zip"),
        sources=sources, items=result), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cnt = collections.Counter((v["lacunas"] == 0 or v["transcricao_manual"], v["content"] is not None) for v in result.values())
    print(len(result), "questões; (sem lacuna aberta, com conteúdo) =", dict(cnt))


if __name__ == "__main__":
    main()
