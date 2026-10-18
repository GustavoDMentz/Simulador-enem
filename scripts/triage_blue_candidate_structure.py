#!/usr/bin/env python3
"""Read-only structural triage of ENEM PDF text candidates.

A-E detection is heuristic; a structurally plausible candidate is NOT
validated against the official PDF and must never be auto-published.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

OPTION = re.compile(r"(?<!\w)([A-E])\s*[).]\s+")
HEADING = re.compile(r"QUEST[ÃA]O\s*\d{1,3}", re.I)

def inspect(q):
    if q["status"] != "CANDIDATE_UNVERIFIED":
        return {"ano": q["ano"], "dia": q["dia"], "posicao": q["posicao"],
                "status": "BLOCKED", "reason": q["status"]}
    text = q.get("candidate_text") or ""
    options = [m.group(1) for m in OPTION.finditer(text)]
    distinct = set(options)
    reasons = []
    if len(text) < 120:
        reasons.append("TEXT_TOO_SHORT")
    if len(text) > 15000:
        reasons.append("TEXT_UNUSUALLY_LONG")
    if not HEADING.search(text):
        reasons.append("HEADING_NOT_IN_CANDIDATE")
    if distinct != set("ABCDE"):
        reasons.append("OPTIONS_A_E_NOT_DETECTED")
    if len(options) != 5:
        reasons.append("OPTION_MARKER_COUNT_NOT_FIVE")
    if len(HEADING.findall(text)) > 1:
        reasons.append("MULTIPLE_QUESTION_HEADINGS")
    return {
        "ano": q["ano"], "dia": q["dia"], "posicao": q["posicao"],
        "status": "STRUCTURE_PLAUSIBLE_UNVERIFIED" if not reasons else "NEEDS_EXTRACTION_REVIEW",
        "reason": reasons,
        "text_length": len(text),
        "option_markers": options,
        "pdf_page": q.get("pdf_page"),
        "column": q.get("column"),
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("/tmp/enem-blue-auto-candidates.json"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-structural-triage.json"))
    args = p.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not data.get("read_only") or data.get("total") != len(data.get("questions", [])):
        raise ValueError("Input candidate report invalid")
    results = [inspect(q) for q in data["questions"]]
    summary = dict(Counter(q["status"] for q in results))
    reasons = Counter(reason for q in results for reason in
                      (q["reason"] if isinstance(q["reason"], list) else [q["reason"]]))
    output = {
        "read_only": True, "total": len(results), "summary": summary,
        "reason_counts": dict(reasons),
        "warning": "Heuristic plausibility is not content fidelity or publication authorization.",
        "questions": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(results), "summary": summary,
                      "reason_counts": dict(reasons), "output": str(args.output)},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
