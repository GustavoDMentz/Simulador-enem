#!/usr/bin/env python3
"""
Carga no ArangoDB: JSONL unificado -> Grafo + Documentos
"""

import json
import sys
from pathlib import Path
from arango import ArangoClient
from loguru import logger

# ─── Config ──────────────────────────────────────────────────────────────
ARANGO_HOST = "http://localhost:8529"
ARANGO_USER = "root"
ARANGO_PASS = ""  # Sem senha (ARANGO_NO_AUTH=1)
DB_NAME = "enem"
INPUT_FILE = Path("/home/gumentz/enem-pipeline/data/fused/questoes_enem_2025_AZUL_D1.jsonl")

# ─── Collections / Edge Definitions ──────────────────────────────────────
VERTEX_COLLECTIONS = [
    "Questoes",       # Questões do ENEM
    "Habilidades",    # Códigos de habilidade (CO_HABILIDADE)
    "Areas",          # CH, CN, LC, MT
    "Provas",         # ANO_COR_DIA (ex: 2025_AZUL_D1)
    "ParametrosTRI",  # a, b, c por questão
    "Itens",          # CO_ITEM (código INEP)
]

EDGE_COLLECTIONS = [
    ("QuestaoHabilidade", "Questoes", "Habilidades"),
    ("QuestaoProva", "Questoes", "Provas"),
    ("QuestaoParamTRI", "Questoes", "ParametrosTRI"),
    ("QuestaoItem", "Questoes", "Itens"),
    ("HabilidadeArea", "Habilidades", "Areas"),
]

def criar_estrutura(db):
    """Cria collections, índices e edge definitions."""
    logger.info("Criando estrutura do banco...")
    
    # Vertex collections
    for name in VERTEX_COLLECTIONS:
        if not db.has_collection(name):
            db.create_collection(name=name)
            logger.info(f"  Vertex: {name}")
        else:
            logger.debug(f"  Vertex existe: {name}")
    
    # Edge collections
    for name, from_col, to_col in EDGE_COLLECTIONS:
        if not db.has_collection(name):
            db.create_collection(name=name, edge=True)
            logger.info(f"  Edge: {name} ({from_col} -> {to_col})")
        else:
            logger.debug(f"  Edge existe: {name}")
    
    # Índices
    # Questoes
    q = db["Questoes"]
    q.add_index({"type": "persistent", "fields": ["co_item"], "unique": False, "name": "idx_co_item"})
    q.add_index({"type": "fulltext", "fields": ["conteudo.enunciado"], "name": "idx_enunciado_fulltext"})
    q.add_index({"type": "persistent", "fields": ["ano", "cor_prova", "dia"], "name": "idx_ano_cor_dia"})
    q.add_index({"type": "persistent", "fields": ["area_conhecimento"], "name": "idx_area"})
    
    # ParametrosTRI
    pt = db["ParametrosTRI"]
    pt.add_index({"type": "persistent", "fields": ["b_dificuldade"], "name": "idx_b_dificuldade"})
    pt.add_index({"type": "persistent", "fields": ["a_discriminacao"], "name": "idx_a_discriminacao"})
    
    # Provas
    p = db["Provas"]
    # _key já é indexado automaticamente
    
    logger.success("Estrutura criada/validada")

def carregar_questoes(db, input_path: Path) -> dict:
    """Carrega JSONL no grafo."""
    q_col = db["Questoes"]
    ph_col = db["QuestaoHabilidade"]
    pp_col = db["QuestaoProva"]
    qtri_edge_col = db["QuestaoParamTRI"]
    qi_col = db["QuestaoItem"]
    h_col = db["Habilidades"]
    a_col = db["Areas"]
    p_col = db["Provas"]
    i_col = db["Itens"]
    ha_col = db["HabilidadeArea"]
    
    stats = {"questoes": 0, "edges": 0, "erros": 0}
    
    # Coleta todos os dados primeiro
    questoes = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            questoes.append(json.loads(line.strip()))
    
    logger.info(f"Processando {len(questoes)} questões...")
    
    # 1. Upsert all vertex collections first (batch)
    # Habilidades
    hab_keys = set(f"HAB_{q['co_habilidade']}" for q in questoes)
    for hab_key in hab_keys:
        if not h_col.has(hab_key):
            h_col.insert({"_key": hab_key, "codigo": int(hab_key.split("_")[1])})
    
    # Areas
    area_keys = set(q["area_conhecimento"] for q in questoes)
    for area_key in area_keys:
        if not a_col.has(area_key):
            a_col.insert({"_key": area_key, "nome": area_key})
    
    # Provas
    prova_keys = set(f"{q['ano']}_{q['cor_prova']}_D{q['dia']}" for q in questoes)
    for prova_key in prova_keys:
        if not p_col.has(prova_key):
            parts = prova_key.split("_")
            p_col.insert({"_key": prova_key, "ano": int(parts[0]), "cor": parts[1], "dia": int(parts[2][1:])})
    
    # Itens (CO_ITEM)
    item_keys = set(f"ITEM_{q['co_item']}" for q in questoes)
    for item_key in item_keys:
        if not i_col.has(item_key):
            i_col.insert({"_key": item_key, "co_item": int(item_key.split("_")[1])})
    
    # HabilidadeArea edges
    for q in questoes:
        hab_key = f"HAB_{q['co_habilidade']}"
        area_key = q["area_conhecimento"]
        edge_key = f"{hab_key}_{area_key}"
        if not ha_col.has(edge_key):
            ha_col.insert({
                "_key": edge_key,
                "_from": f"Habilidades/{hab_key}",
                "_to": f"Areas/{area_key}"
            })
    
    # 2. Agora processa questões e edges
    for doc in questoes:
        try:
            key = doc["id_unico_sistema"]
            
            # Questao vertex
            doc["_key"] = key
            q_col.insert(doc, overwrite=True)
            stats["questoes"] += 1
            
            # ParamTRI vertex (one per questao)
            tri_key = f"TRI_{key}"
            tri_doc = {
                "_key": tri_key,
                "a_discriminacao": doc["parametros_tri"]["a_discriminacao"],
                "b_dificuldade": doc["parametros_tri"]["b_dificuldade"],
                "c_chute": doc["parametros_tri"]["c_chute"]
            }
            pt_col.insert(tri_doc, overwrite=True)
            
            # Garante que vértices existem antes das edges
            hab_key = f"HAB_{doc['co_habilidade']}"
            prova_key = f"{doc['ano']}_{doc['cor_prova']}_D{doc['dia']}"
            item_key = f"ITEM_{doc['co_item']}"
            
            # Cria vértices se não existirem (race condition protection)
            if not h_col.has(hab_key):
                h_col.insert({"_key": hab_key, "codigo": doc["co_habilidade"]})
            if not p_col.has(prova_key):
                parts = prova_key.split("_")
                p_col.insert({"_key": prova_key, "ano": int(parts[0]), "cor": parts[1], "dia": int(parts[2][1:])})
            if not i_col.has(item_key):
                i_col.insert({"_key": item_key, "co_item": doc["co_item"]})
            
            # HabilidadeArea edge
            area_key = doc["area_conhecimento"]
            ha_edge_key = f"{hab_key}_{area_key}"
            if not ha_col.has(ha_edge_key):
                ha_col.insert({
                    "_key": ha_edge_key,
                    "_from": f"Habilidades/{hab_key}",
                    "_to": f"Areas/{area_key}"
                })
            
            # Edges
            edges = [
                (ph_col, f"Questoes/{key}", f"Habilidades/{hab_key}", {"ano": doc["ano"]}),
                (pp_col, f"Questoes/{key}", f"Provas/{prova_key}", {"posicao": doc["posicao_prova"]}),
                (qtri_edge_col, f"Questoes/{key}", f"ParametrosTRI/{tri_key}", {
                    "a": doc["parametros_tri"]["a_discriminacao"],
                    "b": doc["parametros_tri"]["b_dificuldade"],
                    "c": doc["parametros_tri"]["c_chute"]
                }),
                (qi_col, f"Questoes/{key}", f"Itens/{item_key}", {}),
            ]
            
            for col, from_v, to_v, attrs in edges:
                edge = {"_key": f"{key}_{col.name}", "_from": from_v, "_to": to_v, **attrs}
                col.insert(edge, overwrite=True)
                stats["edges"] += 1
            
        except Exception as e:
            stats["erros"] += 1
            logger.error(f"Questão {doc.get('id_unico_sistema', '?')}: {e}")
            if stats["erros"] > 20:
                break
    
    return stats

def main():
    logger.add("/home/gumentz/enem-pipeline/logs/load_arangodb.log", rotation="10 MB")
    logger.info("=== CARGA ARANGODB ===")
    
    if not INPUT_FILE.exists():
        logger.error(f"Arquivo não encontrado: {INPUT_FILE}")
        sys.exit(1)
    
    # Conecta
    from arango import ArangoClient
    client = ArangoClient(hosts=ARANGO_HOST)
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASS)
    
    # Cria database se não existe
    if not sys_db.has_database(DB_NAME):
        sys_db.create_database(DB_NAME, users=[{"username": ARANGO_USER, "password": ARANGO_PASS}])
        logger.info(f"Database '{DB_NAME}' criado")
    
    db = client.db(DB_NAME, username=ARANGO_USER, password=ARANGO_PASS)
    
    # Cria estrutura
    criar_estrutura(db)
    
    # Carrega dados
    stats = carregar_questoes(db, INPUT_FILE)
    
    logger.success(f"Carga concluída: {stats}")
    
    # Teste AQL
    logger.info("Testando consulta AQL...")
    resultado = db.aql.execute("""
        FOR q IN Questoes
            FILTER q.ano == 2025 AND q.cor_prova == "AZUL" AND q.dia == 1
            SORT q.posicao_prova
            LIMIT 5
            RETURN {
                id: q._key,
                pos: q.posicao_prova,
                b: q.parametros_tri.b_dificuldade,
                gabarito: q.gabarito_oficial,
                area: q.area_conhecimento
            }
    """)
    for r in resultado:
        logger.info(f"  {r}")

if __name__ == "__main__":
    main()