#!/usr/bin/env python3
"""Read-only ArangoDB graph integrity and coverage check. Never writes data."""
import argparse
import json
import os
from pathlib import Path

EDGES = {
    "QuestaoHabilidade": ("Questoes", "Habilidades"),
    "QuestaoProva": ("Questoes", "Provas"),
    "QuestaoParamTRI": ("Questoes", "ParametrosTRI"),
    "QuestaoItem": ("Questoes", "Itens"),
    "HabilidadeArea": ("Habilidades", "Areas"),
}
VERTICES = ("Questoes", "Habilidades", "Areas", "Provas", "ParametrosTRI", "Itens")

def inspect(db):
    issues = []
    counts = {}
    for name in VERTICES:
        if not db.has_collection(name):
            issues.append({"code": "MISSING_COLLECTION", "collection": name})
        else:
            counts[name] = db.collection(name).count()
    for name, (left, right) in EDGES.items():
        if not db.has_collection(name):
            issues.append({"code": "MISSING_EDGE_COLLECTION", "collection": name})
            continue
        col = db.collection(name)
        counts[name] = col.count()
        if col.properties().get("type") != 3:
            issues.append({"code": "NOT_EDGE_COLLECTION", "collection": name})
            continue
        for direction, target in (("_from", left), ("_to", right)):
            query = """
            FOR e IN @@collection
              FILTER !IS_STRING(e[@field]) OR
                !STARTS_WITH(e[@field], CONCAT(@target, "/")) OR
                DOCUMENT(e[@field]) == null
              COLLECT WITH COUNT INTO n
              RETURN n
            """
            n = list(db.aql.execute(query, bind_vars={
                "@collection": name, "field": direction, "target": target
            }))[0]
            if n:
                issues.append({"code": "INVALID_EDGE_ENDPOINT", "collection": name,
                               "field": direction, "count": n})
    if db.has_collection("Questoes"):
        for code, query in {
            "MISSING_TRI": "FOR q IN Questoes FILTER q.parametros_tri == null COLLECT WITH COUNT INTO n RETURN n",
            "MISSING_CO_ITEM": "FOR q IN Questoes FILTER q.co_item == null COLLECT WITH COUNT INTO n RETURN n",
            "MISSING_PROOF_POSITION": "FOR q IN Questoes FILTER q.posicao_prova == null COLLECT WITH COUNT INTO n RETURN n",
            "DUPLICATE_PROOF_POSITION": """FOR q IN Questoes
              COLLECT ano=q.ano, dia=q.dia, cor=q.cor_prova, pos=q.posicao_prova WITH COUNT INTO n
              FILTER n > 1 COLLECT WITH COUNT INTO total RETURN total""",
        }.items():
            n = list(db.aql.execute(query))[0]
            if n:
                issues.append({"code": code, "count": n})
    return {"schema_version": 1, "read_only": True, "counts": counts,
            "issues": issues, "ok": not issues}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    from arango import ArangoClient
    host = os.environ.get("ARANGO_HOST", "http://127.0.0.1:8529")
    name = os.environ.get("ARANGO_DB", "enem")
    user = os.environ.get("ARANGO_USER")
    password = os.environ.get("ARANGO_PASSWORD")
    if not user or not password:
        raise SystemExit("Set ARANGO_USER and ARANGO_PASSWORD; unauthenticated mode is not supported")
    db = ArangoClient(hosts=host).db(name, username=user, password=password)
    report = inspect(db)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    raise SystemExit(0 if report["ok"] else 1)

if __name__ == "__main__":
    main()
