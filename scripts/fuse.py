#!/usr/bin/env python3
"""
Fusão: Extração LLM (JSON) + Parâmetros TRI (Parquet) → JSONL Unificado
Chave de JOIN: (ano, cor_prova, dia, posicao_prova) ↔ (NU_ANO, TX_COR, CO_POSICAO)

O mapeamento CO_PROVA → (cor, dia) é crítico e deve ser validado por ano.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional
from loguru import logger
from pydantic import ValidationError

# Importa schemas
import sys
sys.path.insert(0, str(Path(__file__).parent))
from schemas import (
    QuestaoEnem, ConteudoQuestao, Alternativas, MetadadosVisual, ParametrosTRI, AreaConhecimento
)

# Mapeamentos
MAP_COR = {
    'AZUL': 'AZUL', 'AMARELA': 'AMARELO', 'AMARELO': 'AMARELO',
    'BRANCA': 'BRANCO', 'BRANCO': 'BRANCO', 'ROSA': 'ROSA', 'VERDE': 'VERDE',
    'LARANJA': 'LARANJA', 'CINZA': 'CINZA', 'LILAS': 'LILAS', 'ROXA': 'LILAS',
    'LEITOR TELA': 'LEITOR_TELA', 'LEITOR_TELA': 'LEITOR_TELA',
    'LARANJA - BRAILE': 'BRAILE', 'BRAILE': 'BRAILE',
    'VERDE - LIBRAS': 'VERDE_LIBRAS', 'VERDE_LIBRAS': 'VERDE_LIBRAS',
}

MAP_AREA = {
    'CH': 'CH', 'CN': 'CN', 'LC': 'LC', 'MT': 'MT',
    '1': 'CH', '2': 'CN', '3': 'LC', '4': 'MT',
}

# Mapeamento CO_PROVA → (cor, dia) por ano
# Baseado nos dados reais do CSV ITENS_PROVA
MAP_PROVA_ANO = {
    2017: {
        396: ('AZUL', 1), 412: ('VERDE', 2), 395: ('AMARELO', 1), 408: ('BRANCO', 1),
        435: ('ROSA', 1), 437: ('LARANJA', 1), 397: ('CINZA', 1), 436: ('AZUL', 2),
        398: ('AMARELO', 2), 438: ('BRANCO', 2),
    },
    2018: {
        496: ('AMARELO', 1), 456: ('AMARELO', 1), 458: ('BRANCO', 1), 495: ('ROSA', 1),
        497: ('LARANJA', 1), 455: ('VERDE', 2), 465: ('CINZA', 2), 457: ('AZUL', 2),
        469: ('LARANJA', 2), 498: ('BRANCO', 2),
    },
    2019: {
        551: ('AZUL', 1), 565: ('LARANJA', 1), 553: ('BRANCO', 1), 513: ('ROSA', 1),
        554: ('AMARELO', 1), 512: ('VERDE', 2), 521: ('CINZA', 2), 525: ('AZUL', 2),
        514: ('LARANJA', 2), 511: ('BRANCO', 2),
    },
    2020: {
        623: ('LARANJA', 1), 620: ('BRANCO', 1), 624: ('ROSA', 1), 619: ('AMARELO', 1),
        617: ('LARANJA', 1), 663: ('VERDE', 2), 657: ('CINZA', 2), 618: ('AZUL', 2),
        664: ('LARANJA', 2), 658: ('BRANCO', 2),
    },
    2021: {
        909: ('AZUL', 1), 910: ('AMARELO', 1), 911: ('BRANCO', 1), 912: ('ROSA', 1), 913: ('LARANJA', 1),
        914: ('VERDE', 2), 915: ('CINZA', 2), 916: ('AZUL', 2), 917: ('LARANJA', 2),
        989: ('LEITOR_TELA', 1),
    },
    2022: {
        1055: ('AZUL', 1), 1056: ('AMARELO', 1), 1057: ('BRANCO', 1), 1058: ('ROSA', 1), 1059: ('LARANJA', 1),
        1060: ('VERDE', 2), 1061: ('CINZA', 2), 1062: ('AZUL', 2), 1063: ('LARANJA', 2),
        1065: ('LEITOR_TELA', 1),
    },
    2023: {
        1286: ('AMARELO', 1), 1282: ('ROSA', 1), 1243: ('LARANJA', 1), 1308: ('BRANCO', 1), 1284: ('AZUL', 1),
        1271: ('VERDE', 2), 1295: ('CINZA', 2), 1315: ('AZUL', 2), 1314: ('LARANJA', 2),
        1253: ('LEITOR_TELA', 1),
    },
    2024: {
        1395: ('AZUL', 1), 1353: ('AMARELO', 1), 1441: ('LARANJA', 1), 1354: ('LILAS', 1), 1442: ('BRANCO', 1),
        1401: ('VERDE', 2), 1402: ('CINZA', 2), 1403: ('AZUL', 2), 1404: ('LARANJA', 2),
        1406: ('LEITOR_TELA', 1),
    },
    2025: {
        1462: ('AZUL', 1), 1463: ('LARANJA', 1), 1464: ('LILAS', 1), 1465: ('AMARELO', 1), 1466: ('BRANCO', 1),
        1467: ('VERDE', 2), 1468: ('CINZA', 2), 1469: ('AZUL', 2), 1470: ('LARANJA', 2),
        1496: ('LEITOR_TELA', 1),
    },
}

def load_llm_json(path: Path) -> list[dict]:
    """Carrega JSON extraído pelo LLM."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"LLM JSON: {len(data)} questões de {path.name}")
    return data

def load_tri_parquet(path: Path, ano: int) -> pd.DataFrame:
    """Carrega Parquet TRI e filtra ano + válidos."""
    df = pd.read_parquet(path)
    logger.info(f"TRI Parquet: {len(df)} linhas totais")
    
    # Filtra ano
    df = df[df['NU_ANO'] == ano].copy()
    logger.info(f"  Ano {ano}: {len(df)} linhas")
    
    # Filtra válidos (não anulados)
    df_validos = df[df['IN_ITEM_ABAN'] == 0].copy()
    logger.info(f"  Válidos (IN_ITEM_ABAN=0): {len(df_validos)}")
    
    # Normaliza cor
    df_validos['TX_COR_NORM'] = df_validos['TX_COR'].str.upper().str.strip().map(MAP_COR).fillna(df_validos['TX_COR'].str.upper().str.strip())
    
    if ano == 2017:
        logger.info("  [2017] Ajustando posições para absoluto (CN += 90, MT += 135)")
        # Usa .loc com cópia explícita ou conversão para evitar SettingWithCopyWarning
        is_cn = df_validos['SG_AREA'] == 'CN'
        is_mt = df_validos['SG_AREA'] == 'MT'
        df_validos.loc[is_cn, 'CO_POSICAO'] = df_validos.loc[is_cn, 'CO_POSICAO'] + 90
        df_validos.loc[is_mt, 'CO_POSICAO'] = df_validos.loc[is_mt, 'CO_POSICAO'] + 135
    
    return df_validos

def inferir_dia_por_prova(co_prova: int, ano: int) -> tuple[str, int]:
    """Retorna (cor, dia) dado CO_PROVA e ano."""
    if ano in MAP_PROVA_ANO and co_prova in MAP_PROVA_ANO[ano]:
        return MAP_PROVA_ANO[ano][co_prova]
    # Fallback: tenta inferir pela cor
    return None, None

def fundir(llm_data: list[dict], df_tri: pd.DataFrame, ano: int, cor_alvo: str, dia_alvo: int) -> list[QuestaoEnem]:
    """
    Junta extração LLM com TRI.
    """
    # Filtra TRI para a cor/dia alvo
    tri_filtrado = df_tri[df_tri['TX_COR_NORM'] == cor_alvo.upper()].copy()
    logger.info(f"TRI filtrado {cor_alvo} D{dia_alvo}: {len(tri_filtrado)} questões")
    
    # Indexa por posição
    tri_idx = tri_filtrado.set_index('CO_POSICAO')
    
    resultados = []
    erros = []
    
    for q_llm in llm_data:
        pos = q_llm['posicao']
        
        if pos not in tri_idx.index:
            erros.append(f"Q{pos}: posição não encontrada no TRI para {cor_alvo} D{dia_alvo}")
            logger.warning(f"  Q{pos}: sem match no TRI")
            continue
        
        tri_row = tri_idx.loc[pos]
        
        # Se múltiplas linhas (duplicatas), pega a primeira
        if isinstance(tri_row, pd.DataFrame):
            tri_row = tri_row.iloc[0]
        
        # Validações
        if tri_row['CO_ITEM'] is None or pd.isna(tri_row['CO_ITEM']):
            erros.append(f"Q{pos}: CO_ITEM nulo no TRI")
            continue
        
        if pd.isna(tri_row['NU_PARAM_A']) or pd.isna(tri_row['NU_PARAM_B']) or pd.isna(tri_row['NU_PARAM_C']):
            erros.append(f"Q{pos}: parâmetros TRI nulos")
            logger.warning(f"  Q{pos}: TRI params nulos")
            continue
        
        # Constrói objeto unificado
        try:
            questao = QuestaoEnem(
                id_unico_sistema=f"{ano}_{cor_alvo.upper()}_D{dia_alvo}_Q{str(pos).zfill(2)}",
                co_item=int(tri_row['CO_ITEM']),
                ano=ano,
                dia=dia_alvo,
                cor_prova=cor_alvo.upper(),
                posicao_prova=pos,
                area_conhecimento=AreaConhecimento(MAP_AREA.get(str(tri_row['SG_AREA']).upper(), 'CH')),
                gabarito_oficial=str(tri_row['TX_GABARITO']).upper(),
                co_habilidade=int(tri_row['CO_HABILIDADE']) if pd.notna(tri_row['CO_HABILIDADE']) else 0,
                conteudo=ConteudoQuestao(
                    enunciado=q_llm['enunciado'],
                    texto_base=q_llm.get('texto_base', ''),
                    alternativas=Alternativas(**q_llm['alternativas']),
                    metadados_visual=MetadadosVisual(**q_llm['metadados_visual'])
                ),
                parametros_tri=ParametrosTRI(
                    a_discriminacao=float(tri_row['NU_PARAM_A']),
                    b_dificuldade=float(tri_row['NU_PARAM_B']),
                    c_chute=float(tri_row['NU_PARAM_C'])
                )
            )
            resultados.append(questao)
            
        except ValidationError as e:
            erros.append(f"Q{pos}: validação Pydantic falhou - {e}")
            logger.error(f"  Q{pos}: {e}")
        except Exception as e:
            erros.append(f"Q{pos}: erro inesperado - {e}")
            logger.error(f"  Q{pos}: {e}")
    
    if erros:
        logger.warning(f"Total de erros/avisos: {len(erros)}")
        for e in erros[:10]:
            logger.warning(f"  - {e}")
    
    logger.success(f"Fusão concluída: {len(resultados)} questões válidas")
    return resultados

def salvar_jsonl(questoes: list[QuestaoEnem], output_path: Path):
    """Salva como JSONL (uma linha por documento)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for q in questoes:
            f.write(q.model_dump_json() + '\n')
    logger.info(f"Salvo: {output_path} ({output_path.stat().st_size/1e6:.2f} MB)")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fusão LLM + TRI")
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--cor", type=str, required=True, help="Cor da prova (AZUL, AMARELO, etc.)")
    parser.add_argument("--dia", type=int, required=True, choices=[1, 2])
    parser.add_argument("--llm", type=Path, required=True, help="JSON extraído pelo LLM")
    parser.add_argument("--tri", type=Path, required=True, help="Parquet TRI unificado")
    parser.add_argument("--output", type=Path, required=True, help="Arquivo JSONL de saída")
    args = parser.parse_args()
    
    logger.add(f"/home/gumentz/enem-pipeline/logs/fuse_{args.ano}_{args.cor}_D{args.dia}.log", rotation="10 MB")
    logger.info(f"=== FUSÃO {args.ano} {args.cor} D{args.dia} ===")
    
    # Carrega dados
    llm_data = load_llm_json(args.llm)
    df_tri = load_tri_parquet(args.tri, args.ano)
    
    # Fusão
    questoes = fundir(llm_data, df_tri, args.ano, args.cor, args.dia)
    
    # Salva
    salvar_jsonl(questoes, args.output)
    
    # Resumo
    print(f"\n{'='*50}")
    print(f"FUSÃO CONCLUÍDA: {args.ano} {args.cor} Dia {args.dia}")
    print(f"  Questões processadas: {len(questoes)}")
    print(f"  Saída: {args.output}")
    
    if questoes:
        print(f"  Exemplo: {questoes[0].id_unico_sistema}")
        print(f"    b (dificuldade): {questoes[0].parametros_tri.b_dificuldade:.4f}")
        print(f"    a (discriminação): {questoes[0].parametros_tri.a_discriminacao:.4f}")
        print(f"    c (chute): {questoes[0].parametros_tri.c_chute:.4f}")
        print(f"    gabarito: {questoes[0].gabarito_oficial}")
        print(f"    área: {questoes[0].area_conhecimento}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()