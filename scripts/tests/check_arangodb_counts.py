#!/usr/bin/env python3
"""Integration test assertions: compare live graph counts across load and restore."""
import argparse
import json
import os
from pathlib import Path

VERTICES = ("Questoes", "ParametrosTRI")
PER_QUESTION_EDGES = (
    "QuestaoHabilidade", "QuestaoProva", "QuestaoParamTRI", "QuestaoItem")
COLLECTIONS = VERTICES + PER_QUESTION_EDGES + (
    "Habilidades", "Areas", "Provas", "Itens", "HabilidadeArea")

def snapshot(db):
    return {name: db.collection(name).count() for name in COLLECTIONS}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=int, required=True)
    parser.add_argument("--write-snapshot", type=Path)
    parser.add_argument("--compare-snapshot", type=Path)
    args = parser.parse_args()

    from arango import ArangoClient
    db = ArangoClient(hosts=os.environ["ARANGO_HOST"]).db(
        os.environ["ARANGO_DB"],
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"])
    counts = snapshot(db)
    assert counts["Questoes"] == args.expected, counts
    assert counts["ParametrosTRI"] == args.expected, counts
    for name in PER_QUESTION_EDGES:
        assert counts[name] == args.expected, f"{name} has duplicate/missing edges: {counts}"
    assert 0 < counts["HabilidadeArea"] <= args.expected, counts
    assert counts["Itens"] == args.expected, counts

    if args.write_snapshot:
        args.write_snapshot.write_text(json.dumps(counts, indent=2) + "\n")
    if args.compare_snapshot:
        expected = json.loads(args.compare_snapshot.read_text())
        assert counts == expected, f"Counts changed after reload/restore: {counts} != {expected}"
    print(json.dumps({"database": os.environ["ARANGO_DB"], "verified": True, "counts": counts}, indent=2))

if __name__ == "__main__":
    main()
