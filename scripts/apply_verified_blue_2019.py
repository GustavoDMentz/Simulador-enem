#!/usr/bin/env python3
"""Apply source-checked 2018 answer-key and 2019 text corrections to the isolated release.

Run from the repository root:
    python scripts/apply_verified_blue_2019.py

Only generated blue-staging/blue-published JSONL files are changed.
Never modifies fused data or the database. Fails closed on unexpected input.
"""
import json
import os
from collections import Counter
from pathlib import Path

SOURCE = Path("data/blue-staging/release-review/release-candidates.jsonl")
PUBLISHED = Path("data/blue-published/questions.jsonl")
PREVIEW = Path("data/blue-published/preview-questions.jsonl")


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source: {SOURCE}")
    rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    keys = [(row["ano"], row["dia"], row["posicao"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("Duplicate question positions: refusing to publish")
    by_key = dict(zip(keys, rows))
    required = [(2019, 2, 110), (2019, 2, 166)]
    if any(key not in by_key for key in required):
        raise SystemExit("Expected 2019 source records missing")
    # Independently checked against the official INEP 2018 day-2 blue answer key.
    # These questions remain REVIEW_ANSWER: an answer match does not certify content.
    answer_fixes_2018 = {
        117: ("B", "D"),
        139: ("E", "A"),
        150: ("D", "E"),
        162: ("D", "E"),
        169: ("B", "C"),
        176: ("B", "C"),
    }
    for position, (old_answer, official_answer) in answer_fixes_2018.items():
        row = by_key.get((2018, 2, position))
        if row is None or row["status"] != "REVIEW_ANSWER":
            raise SystemExit(f"Unexpected 2018 day-2 question {position}: no files changed")
        stored = row["record"].get("gabarito_oficial")
        if stored not in (old_answer, official_answer):
            raise SystemExit(f"Unexpected answer for 2018 day-2 Q{position}: {stored!r}; no files changed")
    for position, (_, official_answer) in answer_fixes_2018.items():
        by_key[(2018, 2, position)]["record"]["gabarito_oficial"] = official_answer

    q110 = by_key[(2019, 2, 110)]
    q166 = by_key[(2019, 2, 166)]
    c110 = q110["record"]["conteudo"]
    c166 = q166["record"]["conteudo"]
    old = "leis de uniformidade"
    new = "leis da uniformidade"
    base = c110.get("texto_base") or ""
    option = c166["alternativas"].get("A")
    if (old not in base and new not in base) or option not in ("8√22 cm.", "2√22 cm."):
        raise SystemExit("Source content differs from audited evidence; no files changed")
    if q110["record"].get("gabarito_oficial") != "D" or (c110.get("metadados_visual") or {}).get("contem_imagem"):
        raise SystemExit("Question 110 does not satisfy the expected release preconditions")
    if q110["status"] not in ("REVIEW_TEXT", "CANDIDATE"):
        raise SystemExit("Unexpected status for question 110")
    if q166["status"] not in ("REVIEW_TEXT", "REVIEW_IMAGE"):
        raise SystemExit("Unexpected status for question 166")
    if old in base:
        c110["texto_base"] = base.replace(old, new)
    c166["alternativas"]["A"] = "2√22 cm."
    q110["status"] = "CANDIDATE"
    q110["reason"] = "SOURCE_PDF_TEXT_VERIFIED_2019_D2_Q110_AND_MATCHING_EXTRACTED_KEY"

    published = []
    preview = []
    counts = Counter()
    for row in sorted(rows, key=lambda r: (r["ano"], r["dia"], r["posicao"])):
        status = row["status"]
        record = row["record"]
        content = record.get("conteudo") or {}
        options = content.get("alternativas") or {}
        if not str(content.get("enunciado") or "").strip() or any(not str(options.get(k) or "").strip() for k in "ABCDE"):
            raise SystemExit(f"Incomplete question {row['ano']}/{row['dia']}/{row['posicao']}")
        counts[status] += 1
        if status == "CANDIDATE":
            if record.get("gabarito_oficial") not in "ABCDE":
                raise SystemExit("Candidate missing answer key")
            published.append(record.copy())
        if status in ("CANDIDATE", "REVIEW_TEXT", "REVIEW_ANSWER", "REVIEW_IMAGE"):
            item = record.copy()
            if status != "CANDIDATE":
                item["gabarito_oficial"] = None
                item["parametros_tri"] = None
            item["preview_status"] = status
            item["preview_unverified"] = status != "CANDIDATE"
            item["scoring_enabled"] = status == "CANDIDATE"
            item["preview_warning"] = ("Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação."
                if status != "CANDIDATE" else None)
            preview.append(item)
    if len(published) != 20 or len(preview) != 513:
        raise SystemExit(f"Unexpected counts: published={len(published)}, preview={len(preview)}; no files changed")
    write_jsonl(SOURCE, rows)
    write_jsonl(PUBLISHED, published)
    write_jsonl(PREVIEW, preview)
    print(json.dumps({"published": len(published), "preview": len(preview),
                      "statuses": dict(counts), "database_changed": False,
                      "corrected_2018_answers": len(answer_fixes_2018),\n                      "note": "Candidates are not independently certified"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
