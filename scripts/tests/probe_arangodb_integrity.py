#!/usr/bin/env python3
"""Negative integration probes, exclusively for an isolated throwaway ArangoDB."""
import os
from arango import ArangoClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_arangodb_integrity import inspect

def main():
    assert os.environ.get("ARANGO_DB", "").startswith("enem_ci"), "Refuse to corrupt a non-CI database"
    db = ArangoClient(hosts=os.environ["ARANGO_HOST"]).db(
        os.environ["ARANGO_DB"],
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"])
    assert inspect(db)["ok"], "Graph must be clean before probes"
    sample = next(iter(db.aql.execute("FOR q IN Questoes SORT q._key LIMIT 1 RETURN q")))
    second = next(iter(db.aql.execute(
        "FOR q IN Questoes FILTER q._key != @key LIMIT 1 RETURN q", bind_vars={"key": sample["_key"]})))

    # Point an existing edge to another VALID item: no dangling endpoint,
    # but metadata no longer match. The checker must catch that.
    edge_col = db.collection("QuestaoItem")
    edge_key = f"{sample['_key']}_QuestaoItem"
    original = edge_col.get(edge_key)
    assert original is not None
    expected_to = original["_to"]
    wrong_to = f"Itens/ITEM_{second['co_item']}"
    assert wrong_to != expected_to
    try:
        edge_col.update({"_key": edge_key, "_to": wrong_to})
        codes = {x["code"] for x in inspect(db)["issues"]}
        assert "INCORRECT_QUESTION_LINK" in codes, codes
    finally:
        edge_col.update({"_key": edge_key, "_to": expected_to})
    assert inspect(db)["ok"], "Failed to undo edge corruption"

    # A changed TRI vertex must be detected even with all edges intact.
    tri_col = db.collection("ParametrosTRI")
    tri_key = f"TRI_{sample['_key']}"
    original_a = tri_col.get(tri_key)["a_discriminacao"]
    try:
        tri_col.update({"_key": tri_key, "a_discriminacao": 999.0})
        codes = {x["code"] for x in inspect(db)["issues"]}
        assert "TRI_VERTEX_MISMATCH" in codes, codes
    finally:
        tri_col.update({"_key": tri_key, "a_discriminacao": original_a})
    assert inspect(db)["ok"], "Failed to undo TRI corruption"

    # A different document key cannot claim an occupied proof slot.
    counterfeit = {
        "_key": "TEST_DUPLICATE_SLOT",
        "ano": sample["ano"],
        "dia": sample["dia"],
        "cor_prova": sample["cor_prova"],
        "posicao_prova": sample["posicao_prova"],
    }
    try:
        db.collection("Questoes").insert(counterfeit)
    except Exception as exc:
        assert "unique" in str(exc).lower() or "1210" in str(exc), exc
    else:
        db.collection("Questoes").delete(counterfeit["_key"])
        raise AssertionError("Unique proof-slot index did not reject a duplicate")
    assert inspect(db)["ok"], "Duplicate-slot probe damaged the graph"
    print("Negative probes passed: wrong link, TRI drift and duplicate slot rejected")

if __name__ == "__main__":
    main()
