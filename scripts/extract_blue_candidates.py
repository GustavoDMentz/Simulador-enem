#!/usr/bin/env python3
"""Batch-extract *candidate* question text from official blue PDFs.

Uses pdftotext -bbox-layout word coordinates to locate headings and next
headings on a page. Produces candidates, never validated questions. Does not
overwrite fused records or touch databases. Multi-column and continuation
cases are explicitly held for further automated analysis.
"""
import argparse
import csv
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

PATTERN = re.compile(r"QUEST[ÃA]O\s*(\d{1,3})", re.I)

def words_for_pdf(pdf):
    xml = subprocess.run(["pdftotext", "-bbox-layout", str(pdf), "-"],
                         check=True, capture_output=True, text=True).stdout
    xml = "".join(ch for ch in xml if ch in "\\t\\n\\r" or 0x20 <= ord(ch) <= 0xD7FF or 0xE000 <= ord(ch) <= 0xFFFD or 0x10000 <= ord(ch) <= 0x10FFFF)
    root = ET.fromstring(xml)
    pages = []
    for page in root.iter():
        if not page.tag.endswith("page"):
            continue
        words = []
        for w in page.iter():
            if w.tag.endswith("word") and w.text:
                words.append({"text": w.text, "x": float(w.attrib["xMin"]),
                              "y": float(w.attrib["yMin"]), "x_max": float(w.attrib["xMax"]), "y_max": float(w.attrib["yMax"])})
        pages.append(words)
    return pages

def heading_candidates(words):
    found = []
    # Search nearby words on the same line rather than assuming XML word order.
    for i, word in enumerate(words):
        if not re.fullmatch(r"QUEST[ÃA]O", word["text"], re.I):
            continue
        matches = [(j, other) for j, other in enumerate(words)
                   if j != i and abs(other["y"] - word["y"]) < 5
                   and 0 < other["x"] - word["x"] < 110
                   and re.fullmatch(r"\d{1,3}", other["text"])]
        if matches:
            _, nextword = min(matches, key=lambda v: v[1]["x"])
            found.append({"position": int(nextword["text"]),
                          "x": word["x"], "y": word["y"]})
    return found

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=Path("/tmp/enem-blue-recovery-queue.csv"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-auto-candidates.json"))
    args = p.parse_args()
    with args.queue.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_pdf = defaultdict(list)
    for r in rows:
        if r["prova_pdf"]:
            by_pdf[r["prova_pdf"]].append(r)
    extracted = {}
    for pdf in sorted(by_pdf):
        pages = words_for_pdf(pdf)
        found = defaultdict(list)
        for page_num, words in enumerate(pages, 1):
            for heading in heading_candidates(words):
                found[heading["position"]].append((page_num, heading))
        extracted[pdf] = (pages, found)
    results = []
    for r in rows:
        year, day, pos = int(r["ano"]), int(r["dia"]), int(r["posicao"])
        pdf = r["prova_pdf"]
        if not pdf:
            results.append({"ano":year,"dia":day,"posicao":pos,
                            "status":"SOURCE_MISSING","candidate_text":None})
            continue
        pages, found = extracted[pdf]
        hits = found.get(pos, [])
        if len(hits) != 1:
            results.append({"ano":year,"dia":day,"posicao":pos,
                            "status":"HEADING_NOT_UNIQUE","heading_hits":len(hits),
                            "candidate_text":None})
            continue
        page_num, heading = hits[0]
        words = pages[page_num - 1]
        # Restrict to heading's horizontal half to avoid cross-column blending.
        width_mid = (max(w["x"] for w in words) + min(w["x"] for w in words)) / 2 if words else 0
        left = heading["x"] < width_mid
        column = [w for w in words if (w["x"] < width_mid) == left and w["y"] >= heading["y"]]
        # Stop at next heading in same column on this page.
        next_y = min((h["y"] for group in found.values() for pg,h in group
                      if pg == page_num and h["y"] > heading["y"] and
                      (h["x"] < width_mid) == left), default=float("inf"))
        selected = [w for w in column if w["y"] < next_y]
        selected.sort(key=lambda w:(round(w["y"]/4),w["x"]))
        candidate = " ".join(w["text"] for w in selected)
        results.append({
            "ano":year,"dia":day,"posicao":pos,"status":"CANDIDATE_UNVERIFIED",
            "pdf_page":page_num,"column":"left" if left else "right",
            "candidate_text":candidate,
            "warnings":["SINGLE_PAGE_ONLY","LAYOUT_NOT_VALIDATED",
                        "IMAGES_NOT_EXTRACTED","ALTERNATIVES_NOT_VERIFIED"],
        })
    output = {"read_only":True,"total":len(results),
              "warning":"Automatic text candidates are NOT verified question reconstructions.",
              "summary":dict(Counter(r["status"] for r in results)),"questions":results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"total":len(results),"summary":output["summary"],
                      "output":str(args.output)},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
