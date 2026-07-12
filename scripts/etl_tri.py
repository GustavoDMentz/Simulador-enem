#!/usr/bin/env python3
"""
ETL TRI: Carrega todos os CSVs ITENS_PROVA (2017-2025), normaliza e salva Parquet único
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import chardet
import csv

BASE_DIR = Path("/home/gumentz/arquivos_hd/Dados ENEM")
OUTPUT_DIR = Path("/home/gumentz/enem-pipeline/data/tri")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "itens_tri_todos_anos.parquet"

# Mapeamento de colunas que variam por ano
COL_MAP = {
    'NU_ANO': ['NU_ANO', 'ANO'],
    'TX_COR': ['TX_COR', 'CO_PROVA', 'TP_COR', 'SG_COR', 'COR_PROVA'],
    'CO_POSICAO': ['CO_POSICAO', 'NU_POSICAO', 'POSICAO'],
    'CO_ITEM': ['CO_ITEM', 'CO_U_ITEM', 'ITEM'],
    'NU_PARAM_A': ['NU_PARAM_A', 'PARAM_A', 'A'],
    'NU_PARAM_B': ['NU_PARAM_B', 'PARAM_B', 'B'],
    'NU_PARAM_C': ['NU_PARAM_C', 'PARAM_C', 'C'],
    'SG_AREA': ['SG_AREA', 'CO_AREA', 'AREA'],
    'TX_GABARITO': ['TX_GABARITO', 'GABARITO', 'CO_GABARITO'],
    'CO_HABILIDADE': ['CO_HABILIDADE', 'HABILIDADE'],
    'IN_ITEM_ABAN': ['IN_ITEM_ABAN', 'ITEM_ANULADO', 'ANULADO'],
    'TX_MOTIVO_ABAN': ['TX_MOTIVO_ABAN', 'MOTIVO_ANULADO'],
    'CO_PROVA': ['CO_PROVA'],
    'TP_LINGUA': ['TP_LINGUA'],
    'IN_ITEM_ADAPTADO': ['IN_ITEM_ADAPTADO'],
    'TP_VERSAO_DIGITAL': ['TP_VERSAO_DIGITAL'],
}

MAP_AREA_NUM = {'1': 'CH', '2': 'CN', '3': 'LC', '4': 'MT'}
MAP_AREA = {**MAP_AREA_NUM, 'CH': 'CH', 'CN': 'CN', 'LC': 'LC', 'MT': 'MT'}
MAP_COR = {
    'AMARELA': 'AMARELO', 'AMARELO': 'AMARELO',
    'BRANCA': 'BRANCO', 'BRANCO': 'BRANCO',
    'ROSA': 'ROSA', 'VERDE': 'VERDE',
    'LARANJA': 'LARANJA', 'CINZA': 'CINZA', 'CINZENTA': 'CINZA',
    'AZUL': 'AZUL', 'LILAS': 'LILAS',
    'LEITOR TELA': 'LEITOR_TELA', 'LEITOR_TELA': 'LEITOR_TELA',
    'LARANJA - BRAILE': 'BRAILE', 'BRAILE': 'BRAILE',
    'VERDE - LIBRAS': 'VERDE_LIBRAS', 'VERDE_LIBRAS': 'VERDE_LIBRAS',
}

def detectar_delimiter_encoding(caminho: Path):
    with open(caminho, 'rb') as f:
        raw = f.read(8192)
    enc = chardet.detect(raw)['encoding'] or 'latin-1'
    sample = raw.decode(enc, errors='ignore')
    dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
    return dialect.delimiter, enc

def encontrar_coluna(df: pd.DataFrame, candidatos: list) -> str:
    for c in candidatos:
        if c in df.columns:
            return c
    # Tenta case-insensitive
    cols_upper = {c.upper(): c for c in df.columns}
    for c in candidatos:
        if c.upper() in cols_upper:
            return cols_upper[c.upper()]
    raise ValueError(f"Nenhuma das colunas encontradas: {candidatos}. Disponíveis: {list(df.columns)}")

def processar_ano(ano: int) -> pd.DataFrame:
    # Determina caminho do CSV
    if ano == 2023:
        csv_path = BASE_DIR / f"microdados_enem_{ano}" / f"microdados_enem_{ano} atualizado sem as logos" / "DADOS" / f"ITENS_PROVA_{ano}.csv"
    elif ano in [2024, 2025]:
        csv_path = BASE_DIR / f"microdados_enem_{ano}" / f"microdados_enem_{ano}_defeso" / "DADOS" / f"ITENS_PROVA_{ano}.csv"
    else:
        csv_path = BASE_DIR / f"microdados_enem_{ano}" / "DADOS" / f"ITENS_PROVA_{ano}.csv"
    
    logger.info(f"Processando {ano}: {csv_path}")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")
    
    # INEP usa SEMPRE latin-1 e delimitador ';'
    sep = ';'
    enc = 'latin-1'
    logger.debug(f"  Delimitador: '{sep}' | Encoding: {enc} (fixo INEP)")
    
    # Lê com dtype=str para preservar tudo
    df = pd.read_csv(csv_path, sep=sep, encoding=enc, low_memory=False, dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]
    
    logger.debug(f"  Colunas originais: {list(df.columns)}")
    logger.debug(f"  Shape: {df.shape}")
    
    # Mapeia colunas
    cols = {}
    for target, candidates in COL_MAP.items():
        try:
            cols[target] = encontrar_coluna(df, candidates)
        except ValueError:
            if target in ['TP_LINGUA', 'IN_ITEM_ADAPTADO', 'TP_VERSAO_DIGITAL', 'TX_MOTIVO_ABAN', 'NU_ANO']:
                cols[target] = None  # Opcional
            else:
                raise
    
    # Cria DataFrame normalizado
    out = pd.DataFrame()
    out['NU_ANO'] = pd.Series([ano] * len(df), dtype='Int16')
    out['TX_COR'] = df[cols['TX_COR']].str.upper().str.strip().map(MAP_COR).fillna(df[cols['TX_COR']].str.upper().str.strip())
    out['CO_POSICAO'] = pd.to_numeric(df[cols['CO_POSICAO']], errors='coerce').astype('Int16')
    out['CO_ITEM'] = pd.to_numeric(df[cols['CO_ITEM']], errors='coerce').astype('Int32')
    out['NU_PARAM_A'] = pd.to_numeric(df[cols['NU_PARAM_A']].str.replace(',', '.', regex=False), errors='coerce').astype('float32')
    out['NU_PARAM_B'] = pd.to_numeric(df[cols['NU_PARAM_B']].str.replace(',', '.', regex=False), errors='coerce').astype('float32')
    out['NU_PARAM_C'] = pd.to_numeric(df[cols['NU_PARAM_C']].str.replace(',', '.', regex=False), errors='coerce').astype('float32')
    out['SG_AREA'] = df[cols['SG_AREA']].str.upper().str.strip().map(MAP_AREA).fillna(df[cols['SG_AREA']].str.upper().str.strip())
    out['TX_GABARITO'] = df[cols['TX_GABARITO']].str.upper().str.strip()
    out['CO_HABILIDADE'] = pd.to_numeric(df[cols['CO_HABILIDADE']], errors='coerce').astype('Int16')
    out['IN_ITEM_ABAN'] = pd.to_numeric(df[cols['IN_ITEM_ABAN']], errors='coerce').fillna(0).astype('Int8')
    
    if cols['TX_MOTIVO_ABAN'] and cols['TX_MOTIVO_ABAN'] in df.columns:
        out['TX_MOTIVO_ABAN'] = df[cols['TX_MOTIVO_ABAN']].replace('nan', pd.NA)
    else:
        out['TX_MOTIVO_ABAN'] = pd.NA
    
    if cols['CO_PROVA'] and cols['CO_PROVA'] in df.columns:
        out['CO_PROVA'] = pd.to_numeric(df[cols['CO_PROVA']], errors='coerce').astype('Int16')
    else:
        out['CO_PROVA'] = pd.NA
    
    if cols['TP_LINGUA'] and cols['TP_LINGUA'] in df.columns:
        out['TP_LINGUA'] = pd.to_numeric(df[cols['TP_LINGUA']], errors='coerce').astype('Int8')
    else:
        out['TP_LINGUA'] = pd.NA
    
    if cols['IN_ITEM_ADAPTADO'] and cols['IN_ITEM_ADAPTADO'] in df.columns:
        out['IN_ITEM_ADAPTADO'] = pd.to_numeric(df[cols['IN_ITEM_ADAPTADO']], errors='coerce').fillna(0).astype('Int8')
    else:
        out['IN_ITEM_ADAPTADO'] = 0
    
    if cols['TP_VERSAO_DIGITAL'] and cols['TP_VERSAO_DIGITAL'] in df.columns:
        out['TP_VERSAO_DIGITAL'] = pd.to_numeric(df[cols['TP_VERSAO_DIGITAL']], errors='coerce').astype('Int8')
    else:
        out['TP_VERSAO_DIGITAL'] = pd.NA
    
    # Validações
    logger.info(f"  {ano}: {len(out)} linhas | Cores: {out['TX_COR'].unique()} | Posições: {out['CO_POSICAO'].min()}-{out['CO_POSICAO'].max()}")
    
    # Verifica duplicatas por (ano, cor, posicao)
    dup = out.groupby(['NU_ANO', 'TX_COR', 'CO_POSICAO']).size().reset_index(name='count')
    dup = dup[dup['count'] > 1]
    if not dup.empty:
        logger.warning(f"  ⚠ Duplicatas (ano, cor, posicao): {len(dup)} combinações")
        for _, row in dup.head(5).iterrows():
            logger.warning(f"    {row['NU_ANO']} {row['TX_COR']} pos={row['CO_POSICAO']}: {row['count']} linhas")
    
    return out

def main():
    logger.add("/home/gumentz/enem-pipeline/logs/etl_tri.log", rotation="10 MB")
    logger.info("=== INÍCIO ETL TRI (2017-2025) ===")
    
    all_dfs = []
    
    for ano in range(2017, 2026):
        try:
            df = processar_ano(ano)
            all_dfs.append(df)
            logger.success(f"✅ {ano} processado: {len(df)} linhas")
        except Exception as e:
            logger.error(f"❌ {ano} falhou: {e}")
            # Continua com os outros anos
    
    if not all_dfs:
        raise RuntimeError("Nenhum ano processado com sucesso")
    
    # Concatena tudo
    df_final = pd.concat(all_dfs, ignore_index=True)
    
    # Tipos finais otimizados (usa tipos nullable para evitar erro de NaN)
    df_final = df_final.astype({
        'NU_ANO': 'int16',
        'TX_COR': 'string',
        'CO_POSICAO': 'Int16',
        'CO_ITEM': 'Int32',
        'NU_PARAM_A': 'float32',
        'NU_PARAM_B': 'float32',
        'NU_PARAM_C': 'float32',
        'SG_AREA': 'string',
        'TX_GABARITO': 'string',
        'CO_HABILIDADE': 'Int16',
        'IN_ITEM_ABAN': 'Int8',
        'CO_PROVA': 'Int16',
        'TP_LINGUA': 'Int8',
        'IN_ITEM_ADAPTADO': 'Int8',
        'TP_VERSAO_DIGITAL': 'Int8',
    })
    
    # Salva Parquet particionado por ano
    df_final.to_parquet(OUTPUT_FILE, index=False, compression='snappy')
    logger.success(f"💾 Parquet salvo: {OUTPUT_FILE} ({len(df_final):,} linhas, {OUTPUT_FILE.stat().st_size/1e6:.1f} MB)")
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO ETL TRI")
    print("="*60)
    for ano in range(2017, 2026):
        sub = df_final[df_final['NU_ANO'] == ano]
        print(f"{ano}: {len(sub):>6} itens | cores: {sorted(sub['TX_COR'].unique())} | "
              f"pos: {sub['CO_POSICAO'].min()}-{sub['CO_POSICAO'].max()} | "
              f"anulados: {(sub['IN_ITEM_ABAN']==1).sum()}")
    print("="*60)

if __name__ == "__main__":
    main()