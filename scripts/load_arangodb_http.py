#!/usr/bin/env python3
"""
Carga no ArangoDB via API HTTP direta (mais confiável que python-arango wrapper)
"""

import json
import sys
import requests
from pathlib import Path
from loguru import logger

ARANGO_HOST = "http://localhost:8529"
DB_NAME = "enem"
ARANGO_USER = "root"
ARANGO_PASS = ""
INPUT_FILE = Path("/home/gumentz/enem-pipeline/data/fused/questoes_enem_2025_AZUL_D1.jsonl")

session = requests.Session()
session.auth = (ARANGO_USER, ARANGO_PASS) if ARANGO_PASS else None

def arango_post(endpoint, data):
    url = f"{ARANGO_HOST}/_db/{DB_NAME}{endpoint}"
    r = session.post(url, json=data, timeout=30)
    if r.status_code >= 400:
        raise Exception(f"HTTP {r.status_code}: {r.text}")
    return r.json()

def arango_put(endpoint, data):
    url = f"{ARANGO_HOST}/_db/{DB_NAME}{endpoint}"
    r = session.put(url, json=data, timeout=30)
    if r.status_code >= 400:
        raise Exception(f"HTTP {r.status_code}: {r.text}")
    return r.json()

def arango_edge(coll, from_v, to_v, attrs):
    from_key = from_v.split("/")[-1]
    to_key = to_v.split("/")[-1]
    edge_key = f"{from_key}_{to_key}"
    edge_doc = {"_key": edge_key, "_from": from_v, "_to": to_v, **attrs}
    return arango_post(f"/_api/document/{coll}?overwriteMode=replace", edge_doc)

def criar_estrutura():
    logger.info("Criando estrutura via API...")
    
    collections = {
        "Questoes": {"type": "document"},
        "Habilidades": {"type": "document"},
        "Areas": {"type": "document"},
        "Provas": {"type": "document"},
        "ParametrosTRI": {"type": "document"},
        "Itens": {"type": "document"},
        "QuestaoHabilidade": {"type": "edge", "from": ["Questoes"], "to": ["Habilidades"]},
        "QuestaoProva": {"type": "edge", "from": ["Questoes"], "to": ["Provas"]},
        "QuestaoParamTRI": {"type": "edge", "from": ["Questoes"], "to": ["ParametrosTRI"]},
        "QuestaoItem": {"type": "edge", "from": ["Questoes"], "to": ["Itens"]},
        "HabilidadeArea": {"type": "edge", "from": ["Habilidades"], "to": ["Areas"]},
    }
    
    for name, cfg in collections.items():
        try:
            arango_post("/_api/collection", {"name": name, "edge": cfg.get("edge", False)})
            logger.info(f"  Collection criada: {name}")
        except Exception as e:
            if "1207" not in str(e):  # duplicate
                raise
            logger.debug(f"  Collection existe: {name}")
    
    # Índices
    indices = [
        ("Questoes", {"type": "persistent", "fields": ["co_item"], "unique": True}),
        ("Questoes", {"type": "fulltext", "fields": ["conteudo.enunciado"]}),
        ("Questoes", {"type": "persistent", "fields": ["ano", "cor_prova", "dia"]}),
        ("Questoes", {"type": "persistent", "fields": ["area_conhecimento"]}),
        ("ParametrosTRI", {"type": "persistent", "fields": ["b_dificuldade"]}),
        ("ParametrosTRI", {"type": "persistent", "fields": ["a_discriminacao"]}),
    ]
    
    for coll, idx_def in indices:
        try:
            arango_post(f"/_api/index?collection={coll}", idx_def)
            logger.info(f"  Índice: {coll} -> {idx_def}")
        except Exception as e:
            if "1582" not in str(e):  # duplicate index
                logger.warning(f"Índice já existe: {coll} {idx_def}")

def carregar_questoes(input_path: Path):
    logger.info(f"Carregando questões de {input_path}...")
    
    questoes = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            questoes.append(json.loads(line.strip()))
    
    logger.info(f"Processando {len(questoes)} questões...")
    
    # 1. Pre-cria todos os vértices necessários
    # Habilidades
    hab_keys = set(f"HAB_{q['co_habilidade']}" for q in questoes)
    for hab_key in hab_keys:
        try:
            arango_post(f"/_api/document/Habilidades", {"_key": hab_key, "codigo": int(hab_key.split("_")[1])})
        except Exception as e:
            if "1210" not in str(e):  # conflict
                logger.warning(f"Habilidade {hab_key}: {e}")
    
    # Areas
    area_keys = set(q["area_conhecimento"] for q in questoes)
    for area_key in area_keys:
        try:
            arango_post("/_api/document/Areas", {"_key": area_key, "nome": area_key})
        except Exception as e:
            if "1210" not in str(e):
                logger.warning(f"Area {area_key}: {e}")
    
    # Provas
    prova_keys = set(f"{q['ano']}_{q['cor_prova']}_D{q['dia']}" for q in questoes)
    for prova_key in prova_keys:
        try:
            parts = prova_key.split("_")
            arango_post("/_api/document/Provas", {
                "_key": prova_key, 
                "ano": int(parts[0]), 
                "cor": parts[1], 
                "dia": int(parts[2][1:])
            })
        except Exception as e:
            if "1210" not in str(e):
                logger.warning(f"Prova {prova_key}: {e}")
    
    # Itens
    item_keys = set(f"ITEM_{q['co_item']}" for q in questoes)
    for item_key in item_keys:
        try:
            arango_post("/_api/document/Itens", {"_key": item_key, "co_item": int(item_key.split("_")[1])})
        except Exception as e:
            if "1210" not in str(e):
                logger.warning(f"Item {item_key}: {e}")
    
    # Verifica se vértices foram criados
    for coll in ["Habilidades", "Areas", "Provas", "Itens"]:
        count = arango_post("/_api/cursor", {"query": f"RETURN LENGTH(FOR v IN {coll} RETURN v)"})
        logger.info(f"  {coll} vertices: {count['result'][0]}")
    
    # HabilidadeArea edges
    for q in questoes:
        hab_key = f"HAB_{q['co_habilidade']}"
        area_key = q["area_conhecimento"]
        edge_key = f"{hab_key}_{area_key}"
        try:
            arango_edge("HabilidadeArea", f"Habilidades/{hab_key}", f"Areas/{area_key}", {})
        except Exception as e:
            if "1210" not in str(e):
                logger.warning(f"HabilidadeArea {edge_key}: {e}")
    
    # 2. Processa cada questão
    stats = {"questoes": 0, "edges": 0, "erros": 0}
    
    for doc in questoes:
        try:
            key = doc["id_unico_sistema"]
            doc["_key"] = key
            
            # Questao vertex - use POST to create with overwriteMode=replace
            arango_post(f"/_api/document/Questoes?overwriteMode=replace", doc)
            stats["questoes"] += 1
            
            # ParamTRI vertex - use POST to create with overwriteMode=replace
            tri_key = f"TRI_{key}"
            tri_doc = {
                "_key": tri_key,
                "a_discriminacao": doc["parametros_tri"]["a_discriminacao"],
                "b_dificuldade": doc["parametros_tri"]["b_dificuldade"],
                "c_chute": doc["parametros_tri"]["c_chute"]
            }
            arango_post(f"/_api/document/ParametrosTRI?overwriteMode=replace", tri_doc)
            
            # Vértices relacionados
            hab_key = f"HAB_{doc['co_habilidade']}"
            prova_key = f"{doc['ano']}_{doc['cor_prova']}_D{doc['dia']}"
            item_key = f"ITEM_{doc['co_item']}"
            
            # Edges
            arango_edge("QuestaoHabilidade", f"Questoes/{key}", f"Habilidades/{hab_key}", {"ano": doc["ano"]})
            arango_edge("QuestaoProva", f"Questoes/{key}", f"Provas/{prova_key}", {"posicao": doc["posicao_prova"]})
            arango_edge("QuestaoParamTRI", f"Questoes/{key}", f"ParametrosTRI/{tri_key}", {
                "a": doc["parametros_tri"]["a_discriminacao"],
                "b": doc["parametros_tri"]["b_dificuldade"],
                "c": doc["parametros_tri"]["c_chute"]
            })
            arango_edge("QuestaoItem", f"Questoes/{key}", f"Itens/{item_key}", {})
            stats["edges"] += 4
                
        except Exception as e:
            stats["erros"] += 1
            logger.error(f"Questão {doc.get('id_unico_sistema', '?')}: {e}")
            if stats["erros"] > 50:
                break
    
    return stats

def testar_consultas():
    logger.info("Testando consultas AQL...")
    
    queries = [
        # 5 primeiras questões 2025 AZUL D1
        """FOR q IN Questoes
           FILTER q.ano == 2025 AND q.cor_prova == "AZUL" AND q.dia == 1
           SORT q.posicao_prova
           LIMIT 5
           RETURN {id: q._key, pos: q.posicao_prova, b: q.parametros_tri.b_dificuldade, gabarito: q.gabarito_oficial, area: q.area_conhecimento}""",
        
        # Questões com dificuldade > 1.5
        """FOR q IN Questoes
           FILTER q.parametros_tri.b_dificuldade > 1.5
           LIMIT 10
           RETURN {id: q._key, b: q.parametros_tri.b_dificuldade, area: q.area_conhecimento}""",
        
        # Grafo: Questão -> Habilidade -> Area
        """FOR q IN Questoes
           FILTER q._key == "2025_AZUL_D1_Q01"
           FOR v, e IN 1..2 OUTBOUND q._id QuestaoHabilidade, HabilidadeArea
           RETURN {vertex: v._key, edge: e._key}""",
    ]
    
    for i, query in enumerate(queries, 1):
        logger.info(f"Query {i}:")
        try:
            r = session.post(f"{ARANGO_HOST}/_db/{DB_NAME}/_api/cursor", json={"query": query})
            if r.status_code == 201:
                data = r.json()
                for row in data.get("result", []):
                    logger.info(f"  {row}")
            else:
                logger.error(f"  Erro: {r.text}")
        except Exception as e:
            logger.error(f"  Erro query {i}: {e}")

def main():
    logger.add("/home/gumentz/enem-pipeline/logs/load_arangodb_http.log", rotation="10 MB")
    logger.info("=== CARGA ARANGODB (HTTP DIRETO) ===")
    
    import argparse
    parser = argparse.ArgumentParser(description="Carga ArangoDB HTTP")
    parser.add_argument("--input", type=Path, default=INPUT_FILE, help="Caminho do arquivo JSONL fundido")
    args = parser.parse_args()
    input_path = args.input
    
    if not input_path.exists():
        logger.error(f"Arquivo não encontrado: {input_path}")
        sys.exit(1)
    
    criar_estrutura()
    stats = carregar_questoes(input_path)
    logger.success(f"Carga concluída: {stats}")
    
    testar_consultas()

if __name__ == "__main__":
    main()