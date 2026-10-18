#!/usr/bin/env python3
"""Read-only integrity check of an ENEM ArangoDB graph, optionally against fused JSONL."""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

EDGES = {
    "QuestaoHabilidade": ("Questoes", "Habilidades"),
    "QuestaoProva": ("Questoes", "Provas"),
    "QuestaoParamTRI": ("Questoes", "ParametrosTRI"),
    "QuestaoItem": ("Questoes", "Itens"),
    "HabilidadeArea": ("Habilidades", "Areas"),
}
VERTICES = ("Questoes", "Habilidades", "Areas", "Provas", "ParametrosTRI", "Itens")
EXPECTED_RELATIONS = {
    "QuestaoHabilidade": 'CONCAT("Habilidades/HAB_", TO_STRING(q.co_habilidade))',
    "QuestaoProva": 'CONCAT("Provas/", TO_STRING(q.ano), "_", q.cor_prova, "_D", TO_STRING(q.dia))',
    "QuestaoParamTRI": 'CONCAT("ParametrosTRI/TRI_", q._key)',
    "QuestaoItem": 'CONCAT("Itens/ITEM_", TO_STRING(q.co_item))',
}

def count(db, query, bind_vars=None):
    result = list(db.aql.execute(query, bind_vars=bind_vars or {}))
    return int(result[0]) if result else 0

def inspect(db, fused=None):
    """Check collection types, dangling/mismatched relationships, TRI, slot duplicates."""
    issues, counts = [], {}
    present = set()
    for name in VERTICES:
        if not db.has_collection(name):
            issues.append({"code": "MISSING_COLLECTION", "collection": name})
        else:
            present.add(name)
            col = db.collection(name)
            counts[name] = col.count()
            if col.properties().get("type") != 2:
                issues.append({"code": "WRONG_COLLECTION_TYPE", "collection": name})
    for name, (left, right) in EDGES.items():
        if not db.has_collection(name):
            issues.append({"code": "MISSING_EDGE_COLLECTION", "collection": name})
            continue
        present.add(name)
        col = db.collection(name)
        counts[name] = col.count()
        if col.properties().get("type") != 3:
            issues.append({"code": "NOT_EDGE_COLLECTION", "collection": name})
            continue
        for direction, target in (("_from", left), ("_to", right)):
            n = count(db, """
                FOR e IN @@collection
                  FILTER !IS_STRING(e[@field]) OR
                    !STARTS_WITH(e[@field], CONCAT(@target, "/")) OR
                    DOCUMENT(e[@field]) == null
                  COLLECT WITH COUNT INTO n
                  RETURN n
            """, {"@collection": name, "field": direction, "target": target})
            if n:
                issues.append({"code": "INVALID_EDGE_ENDPOINT", "collection": name,
                               "field": direction, "count": n})
        # Pre-v2 importer generated random edge keys, so reruns duplicated links.
        canonical = ('CONCAT(LAST(SPLIT(e._from, "/")), "_", '
                     'LAST(SPLIT(e._to, "/")))' if name == "HabilidadeArea"
                     else 'CONCAT(LAST(SPLIT(e._from, "/")), "_", @name)')
        bad_keys = count(db, f"""
            FOR e IN @@edge
                FILTER e._key != {canonical}
                COLLECT WITH COUNT INTO n
                RETURN n
        """, {"@edge": name, "name": name})
        if bad_keys:
            issues.append({"code": "NONCANONICAL_EDGE_KEY", "collection": name,
                           "count": bad_keys, "message": "Review legacy edges before any reload"})

    if "Questoes" in present:
        for code, query in {
            "MISSING_TRI": 'FOR q IN Questoes FILTER !IS_OBJECT(q.parametros_tri) COLLECT WITH COUNT INTO n RETURN n',
            "MISSING_CO_ITEM": 'FOR q IN Questoes FILTER q.co_item == null COLLECT WITH COUNT INTO n RETURN n',
            "MISSING_PROOF_POSITION": 'FOR q IN Questoes FILTER q.posicao_prova == null COLLECT WITH COUNT INTO n RETURN n',
            "INVALID_GABARITO": 'FOR q IN Questoes FILTER q.gabarito_oficial NOT IN ["A","B","C","D","E"] COLLECT WITH COUNT INTO n RETURN n',
            "DUPLICATE_PROOF_POSITION": """FOR q IN Questoes
                COLLECT ano=q.ano, dia=q.dia, cor=q.cor_prova, pos=q.posicao_prova WITH COUNT INTO n
                FILTER n > 1 COLLECT WITH COUNT INTO total RETURN total""",
        }.items():
            n = count(db, query)
            if n:
                issues.append({"code": code, "count": n})

        for edge, expected in EXPECTED_RELATIONS.items():
            if edge not in present or db.collection(edge).properties().get("type") != 3:
                continue
            # Exactly one edge from every question and its target must match the metadata.
            query = f"""
                FOR q IN Questoes
                    LET endpoints = (FOR e IN @@edge FILTER e._from == q._id RETURN e._to)
                    LET expected = {expected}
                    FILTER LENGTH(endpoints) != 1 OR endpoints[0] != expected
                    COLLECT WITH COUNT INTO n
                    RETURN n
            """
            n = count(db, query, {"@edge": edge})
            if n:
                issues.append({"code": "INCORRECT_QUESTION_LINK", "collection": edge, "count": n})
        if "ParametrosTRI" in present:
            n = count(db, """
                FOR q IN Questoes
                    LET t = DOCUMENT(CONCAT("ParametrosTRI/TRI_", q._key))
                    FILTER t == null OR
                           t.a_discriminacao != q.parametros_tri.a_discriminacao OR
                           t.b_dificuldade != q.parametros_tri.b_dificuldade OR
                           t.c_chute != q.parametros_tri.c_chute
                    COLLECT WITH COUNT INTO n
                    RETURN n
            """)
            if n:
                issues.append({"code": "TRI_VERTEX_MISMATCH", "count": n})
        question_indexes = db.collection("Questoes").indexes()
        coitem_indexes = [i for i in question_indexes if i.get("fields") == ["co_item"]]
        if any(i.get("unique") for i in coitem_indexes):
            issues.append({"code": "UNIQUE_CO_ITEM_INDEX", "message": "CO_ITEM may recur in different booklets"})
        if not any(i.get("fields") == ["ano", "dia", "cor_prova", "posicao_prova"]
                   and i.get("unique") for i in question_indexes):
            issues.append({"code": "MISSING_UNIQUE_PROOF_INDEX"})

    # Missing positions represent content coverage, not malformed graph structure.
    coverage = []
    if "Questoes" in present:
        groups = list(db.aql.execute("""
            FOR q IN Questoes
              COLLECT ano=q.ano, dia=q.dia, cor=q.cor_prova INTO rows = q.posicao_prova
              RETURN {ano:ano, dia:dia, cor:cor, positions:rows}
        """))
        for group in groups:
            if group["dia"] not in (1, 2):
                issues.append({"code": "INVALID_DAY", "group": group})
                continue
            expected = set(range(1, 91)) if group["dia"] == 1 else set(range(91, 181))
            found = set(group["positions"])
            coverage.append({"year": group["ano"], "day": group["dia"], "color": group["cor"],
                             "records": len(group["positions"]),
                             "missing_positions": sorted(expected - found),
                             "unexpected_positions": sorted(found - expected)})

    if fused is not None and "Questoes" in present:
        from load_arangodb import read_questions
        source = {q["id_unico_sistema"]: q for q in read_questions(fused)}
        actual = {q["_key"]: q for q in db.aql.execute("""
            FOR q IN Questoes
                RETURN KEEP(q, "_key", "ano", "dia", "cor_prova", "posicao_prova",
                            "co_item", "co_habilidade", "area_conhecimento",
                            "gabarito_oficial", "parametros_tri")
        """)}
        missing = sorted(set(source) - set(actual))
        extra = sorted(set(actual) - set(source))
        if missing:
            issues.append({"code": "MISSING_FROM_DB", "count": len(missing), "examples": missing[:5]})
        if extra:
            issues.append({"code": "EXTRA_IN_DB", "count": len(extra), "examples": extra[:5]})
        fields = ("ano", "dia", "cor_prova", "posicao_prova", "co_item",
                  "co_habilidade", "area_conhecimento", "gabarito_oficial", "parametros_tri")
        differing = [key for key in source.keys() & actual.keys()
                     if any(source[key].get(field) != actual[key].get(field) for field in fields)]
        if differing:
            issues.append({"code": "DB_SOURCE_MISMATCH", "count": len(differing),
                           "examples": sorted(differing)[:5]})
    return {"schema_version": 2, "read_only": True, "counts": counts,
            "coverage": sorted(coverage, key=lambda r: (r["year"], r["day"], r["color"])),
            "issues": issues, "ok": not issues}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path)
    ap.add_argument("--fused", type=Path, help="Cross-check all DB keys/metadata against these JSONL files")
    ap.add_argument("--legacy-no-auth", action="store_true",
                    help="Diagnose an existing insecure LOCAL instance, read-only")
    args = ap.parse_args()
    from arango import ArangoClient
    host = os.environ.get("ARANGO_HOST", "http://127.0.0.1:8529")
    name = os.environ.get("ARANGO_DB", "enem")
    user = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_PASSWORD")
    if args.legacy_no_auth:
        if urlparse(host).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise SystemExit("--legacy-no-auth is restricted to localhost")
        if password:
            raise SystemExit("Do not combine --legacy-no-auth with ARANGO_PASSWORD")
        print("WARNING: diagnosing legacy unauthenticated LOCAL DB (read-only).", file=sys.stderr)
        password = ""
    elif not user or not password:
        raise SystemExit("Set ARANGO_USER and ARANGO_PASSWORD or use --legacy-no-auth for a LOCAL read-only check")
    db = ArangoClient(hosts=host).db(name, username=user, password=password)
    report = inspect(db, fused=args.fused)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    raise SystemExit(0 if report["ok"] else 1)

if __name__ == "__main__":
    main()
