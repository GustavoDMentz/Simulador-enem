#!/usr/bin/env python3
"""One-command, resumable, non-destructive ENEM blue reconstruction staging.

Produces 1,620 position-level staging records, using existing fused blue
records first and official-PDF text candidates for missing positions.
NEVER treats candidates as verified, NEVER changes ArangoDB/fused data.
Requires poppler-utils. Use --all to process 2017-2025.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_blue_candidates import words_for_pdf, heading_candidates

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def candidate_for(pages, found, position):
    hits = found.get(position, [])
    if len(hits) != 1:
        return {"status": "HEADING_NOT_UNIQUE", "heading_hits": len(hits)}
    page_number, heading = hits[0]
    words = pages[page_number - 1]
    if not words:
        return {"status": "EMPTY_PAGE"}
    mid = (min(w["x"] for w in words) + max(w["x"] for w in words)) / 2
    left = heading["x"] < mid
    stop = min((h["y"] for occurrences in found.values() for pg, h in occurrences
                if pg == page_number and h["y"] > heading["y"]
                and (h["x"] < mid) == left), default=float("inf"))
    chosen = [w for w in words if (w["x"] < mid) == left
              and heading["y"] <= w["y"] < stop]
    chosen.sort(key=lambda w: (w["y"], w["x"]))
    # Preserve source geometry rather than pretending PDF reading order is correct.
    lines = []
    for word in chosen:
        matched = next((line for line in lines if abs(line["y"] - word["y"]) <= 3), None)
        if matched is None:
            matched = {"y": word["y"], "words": []}
            lines.append(matched)
        matched["words"].append(word)
    lines.sort(key=lambda line: line["y"])
    layout_lines = []
    for line in lines:
        ordered = sorted(line["words"], key=lambda w: w["x"])
        layout_lines.append({
            "y": round(line["y"], 2),
            "x_min": round(min(w["x"] for w in ordered), 2),
            "text": " ".join(w["text"] for w in ordered),
            "words": [{"text": w["text"], "x": round(w["x"], 2),
                       "x_max": round(w["x_max"], 2)} for w in ordered],
        })
    # Detect option letters in the left margin of individual visual lines.
    # This is a hypothesis only; it must not certify the option text.
    markers = []
    for index, line in enumerate(layout_lines):
        if not line["words"]:
            continue
        first = line["words"][0]
        if first["text"] in "ABCDE" and len(first["text"]) == 1:
            markers.append({"letter": first["text"], "line_index": index,
                            "y": line["y"], "x": first["x"]})
    return {"status": "TEXT_CANDIDATE_UNVERIFIED",
            "pdf_page": page_number, "column": "left" if left else "right",
            "raw_text": " ".join(w["text"] for w in chosen),
            "layout_lines": layout_lines, "option_marker_hypotheses": markers,
            "option_segmentation": option_segments(layout_lines, markers),
            "warnings": ["SINGLE_PAGE_ONLY", "COLUMN_LAYOUT_UNVERIFIED",
                         "OPTIONS_UNVERIFIED", "OPTION_MARKERS_HEURISTIC", "FIGURES_UNVERIFIED",
                         "CREDITS_UNVERIFIED", "CONTINUATION_UNVERIFIED"]}

def option_segments(layout_lines, markers):
    """Geometric A-E hypotheses; preserve ambiguous cases without guessing."""
    from collections import Counter
    counts = Counter(m["letter"] for m in markers)
    letters = [m["letter"] for m in markers]
    if letters != list("ABCDE") or any(counts[k] != 1 for k in "ABCDE"):
        return {"status": "AMBIGUOUS_MARKERS", "markers": markers,
                "reason": "Markers are missing, repeated or out of sequence"}
    xs = [m["x"] for m in markers]
    if max(xs) - min(xs) > 22:
        return {"status": "AMBIGUOUS_MARKERS", "markers": markers,
                "reason": "Marker horizontal positions disagree"}
    result = {}
    for i, marker in enumerate(markers):
        start = marker["line_index"]
        end = markers[i + 1]["line_index"] if i + 1 < 5 else len(layout_lines)
        parts = []
        for j in range(start, end):
            words = layout_lines[j]["words"]
            if j == start:
                words = [w for w in words if not (
                    w["text"] == marker["letter"] and abs(w["x"] - marker["x"]) < 1)]
            parts.append(" ".join(w["text"] for w in words))
        result[marker["letter"]] = " ".join(p for p in parts if p).strip()
    if any(not result[k] for k in "ABCDE"):
        return {"status": "AMBIGUOUS_MARKERS", "markers": markers,
                "reason": "One or more options empty"}
    return {"status": "GEOMETRIC_HYPOTHESIS_UNVERIFIED",
            "options": result, "markers": markers}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Required for full 2017-2025 run")
    ap.add_argument("--fused", type=Path, default=Path("data/fused"))
    ap.add_argument("--pdf-dir", type=Path, default=Path("data/enem-pdfs/oficiais"))
    ap.add_argument("--output-dir", type=Path, default=Path("data/blue-staging"))
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if not args.all:
        ap.error("Pass --all to run the full canonical staging job")
    if args.output_dir.resolve() == args.fused.resolve() or args.fused.resolve() in args.output_dir.resolve().parents:
        ap.error("Output directory must not be inside data/fused")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fused = defaultdict(list)
    for source in sorted(args.fused.glob("*.jsonl")):
        for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            q = json.loads(line)
            if str(q.get("cor_prova", "")).upper() != "AZUL":
                continue
            key = (int(q["ano"]), int(q["dia"]), int(q["posicao_prova"]))
            fused[key].append({"record": q, "source": str(source), "line": line_no})
    rows, exceptions = [], []
    pdf_cache = {}
    pdf_hashes = {}
    for year in range(2017, 2026):
        for day in (1, 2):
            pdf = args.pdf_dir / f"{year}-regular-d{day}-azul.pdf"
            answer_pdf = args.pdf_dir / f"{year}-regular-d{day}-azul-gabarito.pdf"
            positions = range(1, 91) if day == 1 else range(91, 181)
            for position in positions:
                key = (year, day, position)
                existing = fused.get(key, [])
                item = {
                    "ano": year, "dia": day, "posicao": position,
                    "official_pdf": str(pdf) if pdf.is_file() else None,
                    "official_answer_pdf": str(answer_pdf) if answer_pdf.is_file() else None,
                    "content_verified": False, "answer_verified": False,
                    "tri_verified": False, "publishable": False,
                    "existing_records": existing,
                }
                if len(existing) > 1:
                    item["status"] = "DUPLICATE_BLUE_POSITION"
                elif len(existing) == 1:
                    item["status"] = "REUSE_EXISTING_UNVERIFIED"
                elif not pdf.is_file():
                    item["status"] = "OFFICIAL_PDF_MISSING"
                else:
                    if str(pdf) not in pdf_cache:
                        pages = words_for_pdf(pdf)
                        found = defaultdict(list)
                        for page_number, words in enumerate(pages, 1):
                            for heading in heading_candidates(words):
                                found[heading["position"]].append((page_number, heading))
                        pdf_cache[str(pdf)] = (pages, found)
                        pdf_hashes[str(pdf)] = digest(pdf)
                    pages, found = pdf_cache[str(pdf)]
                    item["extraction"] = candidate_for(pages, found, position)
                    item["status"] = item["extraction"]["status"]
                if item["status"] != "REUSE_EXISTING_UNVERIFIED":
                    exceptions.append({"ano":year,"dia":day,"posicao":position,
                                       "status":item["status"]})
                rows.append(item)
    if len(rows) != 1620:
        raise RuntimeError("Expected 1620 blue positions")
    output = args.output_dir / "blue-candidates.jsonl"
    report = args.output_dir / "report.json"
    missing = args.output_dir / "exceptions.csv"
    # Keep generated data outside tracked sources. No source mutation.
    with output.open("w", encoding="utf-8") as f:
        for item in rows:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    with missing.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ano","dia","posicao","status"])
        writer.writeheader()
        writer.writerows(exceptions)
    summary = dict(Counter(q["status"] for q in rows))
    report.write_text(json.dumps({
        "schema_version": 1, "safe_staging_only": True, "total": len(rows),
        "summary": summary, "exceptions": len(exceptions),
        "pdf_sha256": pdf_hashes,
        "warnings": ["No content, answer or TRI verified",
                     "No automatic publication",
                     "Existing records may contain wrong answers or item links",
                     "Text extraction omits graphics and may truncate continuations"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(rows), "summary": summary,
                      "exceptions": len(exceptions), "output": str(args.output_dir)},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
