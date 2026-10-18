#!/usr/bin/env python3
"""Read-only answer-key evidence for blue staging; never promotes publishability."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from audit_official_gabaritos import extract_pdf

def audit(rows):
    cache = {}
    outcomes = []
    for row in rows:
        year, day, position = int(row["ano"]), int(row["dia"]), int(row["posicao"])
        entry = {"ano": year, "dia": day, "posicao": position,
                 "answer_verified": False, "publishable": False}
        pdf = row.get("official_answer_pdf")
        if not pdf or not Path(pdf).is_file():
            entry.update(status="SOURCE_MISSING", reason="Official answer PDF unavailable")
        else:
            if pdf not in cache:
                path = Path(pdf)
                try:
                    answers, ambiguous, chars = extract_pdf(path)
                    cache[pdf] = (answers, set(ambiguous), chars,
                                  hashlib.sha256(path.read_bytes()).hexdigest(), None)
                except Exception as exc:
                    cache[pdf] = ({}, set(), 0, None, str(exc))
            answers, ambiguous, chars, sha, error = cache[pdf]
            entry["official_answer_pdf_sha256"] = sha
            if error:
                entry.update(status="SOURCE_PARSE_FAILED", reason=error)
            elif any(p not in answers or p in ambiguous
                     for p in (range(1, 91) if day == 1 else range(91, 181))):
                entry.update(status="INCONCLUSIVE_KEY_COVERAGE",
                             reason="Official answer-key parser did not uniquely recover all 90 positions",
                             parsed_positions=len(answers),
                             ambiguous_positions=len(ambiguous))
            elif position in ambiguous or position not in answers:
                entry.update(status="INCONCLUSIVE", reason="Answer row missing or ambiguous")
            elif day == 1 and position <= 5:
                entry.update(status="INCONCLUSIVE_LANGUAGE",
                             reason="Language version not independently identified",
                             official_answers=answers[position])
            elif "comum" not in answers[position]:
                entry.update(status="INCONCLUSIVE", reason="Unexpected answer layout",
                             official_answers=answers[position])
            else:
                official = answers[position]["comum"]
                entry["official_answer"] = official
                if official not in "ABCDE" or len(official) != 1:
                    entry.update(status="INCONCLUSIVE", reason="Noncanonical official mark")
                else:
                    existing = row.get("existing_records") or []
                    if len(existing) != 1:
                        entry.update(status="NO_SINGLE_EXISTING_ANSWER",
                                     reason="Missing or duplicate original record")
                    else:
                        recorded = existing[0]["record"].get("gabarito_oficial")
                        entry["recorded_answer"] = recorded
                        entry["record_id"] = existing[0]["record"].get("id_unico_sistema")
                        entry["status"] = ("ANSWER_TEXT_MATCH_UNVERIFIED"
                                           if recorded == official else "ANSWER_DIVERGENCE")
                        # Official PDF layout and booklet-language mapping have
                        # not received independent verification. Never certify.
        outcomes.append(entry)
    return outcomes

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/blue-staging/blue-candidates.jsonl"))
    p.add_argument("--output-dir", type=Path, default=Path("data/blue-staging"))
    args = p.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    results = audit(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dest = args.output_dir / "official-answer-evidence.jsonl"
    if args.input.resolve() == dest.resolve():
        p.error("Input/output collision")
    with dest.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    summary = {"read_only": True, "total": len(results),
               "summary": dict(Counter(x["status"] for x in results)),
               "answer_verified": 0, "publishable": 0,
               "warning": "PDF answer-key parsing is evidence, not official certification.",
               "details": str(dest)}
    (args.output_dir / "official-answer-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
