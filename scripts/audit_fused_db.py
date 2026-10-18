#!/usr/bin/env python3
"""Read-only integrity report for existing fused ENEM JSONL. No DB writes."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

def audit(root):
    counts = Counter()
    issues = []
    ids = {}
    slots = {}
    item_metadata = {}
    proof_positions = {}
    for file in sorted(Path(root).glob("*.jsonl")):
        for lineno, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            origin = f"{file.name}:{lineno}"
            counts["records"] += 1
            try:
                q = json.loads(raw)
            except json.JSONDecodeError:
                issues.append({"where": origin, "code": "INVALID_JSON"})
                continue
            def issue(code):
                issues.append({"where": origin, "code": code})
            key = q.get("id_unico_sistema")
            if not isinstance(key, str) or not key:
                issue("MISSING_ID")
            elif key in ids:
                issue("DUPLICATE_ID")
            else:
                ids[key] = origin
            year, day, color, pos = (q.get(k) for k in ("ano", "dia", "cor_prova", "posicao_prova"))
            slot = (year, day, color, pos)
            if None in slot:
                issue("MISSING_PROOF_IDENTITY")
            elif slot in slots:
                issue("DUPLICATE_PROOF_POSITION")
            else:
                slots[slot] = origin
                proof_positions.setdefault((year, day, color), set()).add(pos)
            item = q.get("co_item")
            if item is None:
                issue("MISSING_CO_ITEM")
            else:
                # Reuse across colors is legitimate; contradictory area/year metadata is not.
                meta = (year, q.get("area_conhecimento"))
                if item in item_metadata and item_metadata[item] != meta:
                    issue("CONFLICTING_ITEM_METADATA")
                else:
                    item_metadata[item] = meta
            if q.get("gabarito_oficial") not in ("A", "B", "C", "D", "E"):
                issue("MISSING_OR_INVALID_KEY")
            if q.get("in_item_aban") == 1:
                counts["annulled"] += 1
            tri = q.get("parametros_tri")
            if not isinstance(tri, dict):
                issue("MISSING_TRI")
            else:
                for field in ("a_discriminacao", "b_dificuldade", "c_chute"):
                    value = tri.get(field)
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        issue("INVALID_TRI_" + field)
                    elif field == "a_discriminacao" and value <= 0:
                        issue("INVALID_TRI_A")
                    elif field == "c_chute" and not 0 <= value <= 1:
                        issue("INVALID_TRI_C")
            content = q.get("conteudo")
            if not isinstance(content, dict):
                issue("MISSING_CONTENT")
            else:
                opts = content.get("alternativas")
                if not isinstance(opts, dict) or any(not isinstance(opts.get(x), str) or not opts[x].strip() for x in "ABCDE"):
                    issue("INCOMPLETE_OPTIONS")
    counts["unique_ids"] = len(ids)
    counts["unique_proof_slots"] = len(slots)
    counts["unique_co_item"] = len(item_metadata)
    coverage = []
    for (year, day, color), positions in sorted(proof_positions.items()):
        expected = set(range(1, 91)) if day == 1 else set(range(91, 181))
        coverage.append({"year": year, "day": day, "color": color,
                         "records": len(positions),
                         "missing_positions": sorted(expected - positions),
                         "unexpected_positions": sorted(positions - expected)})
    return {"schema_version": 1, "read_only": True,
            "ok": not issues and counts["records"] > 0,
            "counts": dict(counts), "issues": issues, "coverage": coverage}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fused", type=Path, default=Path("data/fused"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    report = audit(args.fused)
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding="utf-8")
    print(data)
    raise SystemExit(0 if report["ok"] else 1)

if __name__ == "__main__":
    main()
