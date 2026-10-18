#!/usr/bin/env python3
"""Idempotent ENEM JSONL -> ArangoDB graph loader.

Dry-run is the default and never connects to or modifies ArangoDB.
Production writes require --apply; database creation additionally needs --create-db.
"""
import argparse
import json
import os
from pathlib import Path

VERTEX_COLLECTIONS = ("Questoes", "Habilidades", "Areas", "Provas", "ParametrosTRI", "Itens")
EDGES = {
    "QuestaoHabilidade": ("Questoes", "Habilidades"),
    "QuestaoProva": ("Questoes", "Provas"),
    "QuestaoParamTRI": ("Questoes", "ParametrosTRI"),
    "QuestaoItem": ("Questoes", "Itens"),
    "HabilidadeArea": ("Habilidades", "Areas"),
}
INDEXES = {
    "Questoes": (
        ("idx_co_item", ("co_item",)),
        ("idx_ano_cor_dia", ("ano", "cor_prova", "dia")),
        ("idx_area", ("area_conhecimento",)),
        ("idx_proof_slot", ("ano", "dia", "cor_prova", "posicao_prova")),
    ),
    "ParametrosTRI": (
        ("idx_b_dificuldade", ("b_dificuldade",)),
        ("idx_a_discriminacao", ("a_discriminacao",)),
    ),
}

def read_questions(source):
    source = Path(source)
    files = sorted(source.glob("*.jsonl")) if source.is_dir() else [source]
    if not files or any(not p.is_file() for p in files):
        raise ValueError(f"No readable JSONL files found: {source}")
    records = []
    seen_ids, seen_slots = set(), set()
    for file in files:
        with file.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                origin = f"{file}:{number}"
                try:
                    item = json.loads(line)
                    key = item["id_unico_sistema"]
                    ano = item["ano"]
                    dia = item["dia"]
                    cor = item["cor_prova"]
                    pos = item["posicao_prova"]
                    tri = item["parametros_tri"]
                    assert isinstance(key, str) and key and "/" not in key
                    assert isinstance(ano, int) and isinstance(dia, int) and dia in (1, 2)
                    assert isinstance(cor, str) and cor
                    assert isinstance(pos, int) and 1 <= pos <= 180
                    assert isinstance(item["co_item"], int)
                    assert isinstance(item["co_habilidade"], int)
                    assert isinstance(item["area_conhecimento"], str)
                    assert item["gabarito_oficial"] in "ABCDE"
                    assert isinstance(tri, dict)
                    assert all(isinstance(tri[k], (float, int)) for k in
                               ("a_discriminacao", "b_dificuldade", "c_chute"))
                    assert tri["a_discriminacao"] > 0
                    assert 0 <= tri["c_chute"] <= 1
                    assert isinstance(item["conteudo"]["alternativas"], dict)
                    assert all(isinstance(item["conteudo"]["alternativas"][a], str) and
                               item["conteudo"]["alternativas"][a].strip() for a in "ABCDE")
                except (ValueError, AssertionError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    raise ValueError(f"Invalid fused record at {origin}: {exc}") from exc
                slot = (ano, dia, cor, pos)
                if key in seen_ids or slot in seen_slots:
                    raise ValueError(f"Duplicate question ID or proof slot at {origin}: {key} {slot}")
                seen_ids.add(key)
                seen_slots.add(slot)
                records.append(item)
    if not records:
        raise ValueError("Empty dataset; refusing to load")
    return records

def _collection(db, name, is_edge=False):
    if not db.has_collection(name):
        db.create_collection(name, edge=is_edge)
    col = db.collection(name)
    properties = col.properties()
    expected_type = 3 if is_edge else 2
    if properties.get("type") != expected_type:
        raise RuntimeError(f"Collection {name} has type {properties.get('type')}, expected {expected_type}")
    return col

def _index(col, name, fields):
    """Enforce intended uniqueness; never silently drop/rebuild conflicting indexes."""
    fields = list(fields)
    unique = name == "idx_proof_slot"
    for idx in col.indexes():
        if idx.get("fields") == fields:
            if bool(idx.get("unique", False)) != unique:
                raise RuntimeError(f"Incompatible index {idx.get('id')} on {col.name}: {fields}. "
                                   "Do not change without backup and migration review.")
            return
    col.add_index({"type": "persistent", "fields": fields, "unique": unique, "name": name})

def criar_estrutura(db):
    for name in VERTEX_COLLECTIONS:
        _collection(db, name)
    for name in EDGES:
        _collection(db, name, is_edge=True)
    for col_name, indexes in INDEXES.items():
        col = db.collection(col_name)
        for name, fields in indexes:
            _index(col, name, fields)

def _upsert(col, document):
    # Stable _key ensures a repeat load replaces the same vertex/edge.
    col.insert(document, overwrite=True, overwrite_mode="replace")

def carregar_questoes(db, source):
    """Preflight all input before writing; upsert stable vertices and edges."""
    records = source if isinstance(source, list) else read_questions(source)
    # Fail BEFORE creating collections or indexes on an older graph.
    # The original loader used server-generated edge keys; reloading into that
    # graph would create duplicate relationships instead of migrating them.
    if db.has_collection("Questoes"):
        for idx in db.collection("Questoes").indexes():
            if idx.get("fields") == ["co_item"] and idx.get("unique"):
                raise RuntimeError("Legacy UNIQUE co_item index found; backup and inspect "
                                   "before a controlled migration. No writes performed.")
    for edge_name in EDGES:
        if db.has_collection(edge_name) and db.collection(edge_name).count():
            if edge_name == "HabilidadeArea":
                continue
            legacy = list(db.aql.execute(
                "FOR e IN @@col FILTER !CONTAINS(e._key, CONCAT('_', @name)) "
                "LIMIT 1 RETURN e._key",
                bind_vars={"@col": edge_name, "name": edge_name}))
            if legacy:
                raise RuntimeError(f"Legacy edge keys detected in {edge_name}; "
                                   "backup and inspect before migration: {legacy[0]}. "
                                   "No writes performed.")
    criar_estrutura(db)
    stats = {"questoes": 0, "edges": 0, "erros": 0}
    for q in records:
        key = q["id_unico_sistema"]
        hab_key = f"HAB_{q['co_habilidade']}"
        area_key = q["area_conhecimento"]
        prova_key = f"{q['ano']}_{q['cor_prova']}_D{q['dia']}"
        item_key = f"ITEM_{q['co_item']}"
        tri_key = f"TRI_{key}"
        _upsert(db.collection("Habilidades"), {"_key": hab_key, "codigo": q["co_habilidade"]})
        _upsert(db.collection("Areas"), {"_key": area_key, "nome": area_key})
        _upsert(db.collection("Provas"), {"_key": prova_key, "ano": q["ano"], "cor": q["cor_prova"], "dia": q["dia"]})
        _upsert(db.collection("Itens"), {"_key": item_key, "co_item": q["co_item"]})
        _upsert(db.collection("Questoes"), {**q, "_key": key})
        tri = q["parametros_tri"]
        _upsert(db.collection("ParametrosTRI"), {"_key": tri_key, **tri})
        relations = (
            ("QuestaoHabilidade", f"Questoes/{key}", f"Habilidades/{hab_key}", {"ano": q["ano"]}),
            ("QuestaoProva", f"Questoes/{key}", f"Provas/{prova_key}", {"posicao": q["posicao_prova"]}),
            ("QuestaoParamTRI", f"Questoes/{key}", f"ParametrosTRI/{tri_key}", {}),
            ("QuestaoItem", f"Questoes/{key}", f"Itens/{item_key}", {}),
        )
        for name, src, target, attrs in relations:
            _upsert(db.collection(name), {
                "_key": f"{key}_{name}", "_from": src, "_to": target, **attrs})
            stats["edges"] += 1
        _upsert(db.collection("HabilidadeArea"), {
            "_key": f"{hab_key}_{area_key}",
            "_from": f"Habilidades/{hab_key}", "_to": f"Areas/{area_key}"})
        stats["questoes"] += 1
    return stats

def connect():
    from arango import ArangoClient
    host = os.environ.get("ARANGO_HOST", "http://127.0.0.1:8529")
    username = os.environ.get("ARANGO_USER")
    password = os.environ.get("ARANGO_PASSWORD")
    if not username or not password:
        raise RuntimeError("Provide ARANGO_USER and ARANGO_PASSWORD. "
                           "Use a secured disposable instance for integration tests.")
    return ArangoClient(hosts=host), username, password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fused", type=Path, default=Path("data/fused"))
    parser.add_argument("--apply", action="store_true", help="Write to ArangoDB (default: dry run)")
    parser.add_argument("--create-db", action="store_true", help="Allow creating missing database, only with --apply")
    args = parser.parse_args()
    records = read_questions(args.fused)
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "records": len(records), "files": str(args.fused),
                          "writes": 0}, indent=2))
        return
    client, username, password = connect()
    name = os.environ.get("ARANGO_DB", "enem")
    system = client.db("_system", username=username, password=password)
    if not system.has_database(name):
        if not args.create_db:
            raise RuntimeError(f"Database {name} does not exist; use --create-db only for new database")
        system.create_database(name)
    db = client.db(name, username=username, password=password)
    stats = carregar_questoes(db, records)
    print(json.dumps({"mode": "apply", "database": name, **stats}, indent=2))

if __name__ == "__main__":
    main()
