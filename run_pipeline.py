#!/usr/bin/env python3
"""
Runner: orquestra o pipeline completo para um ano/cor/dia
"""

import asyncio
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
DATA_DIR = PIPELINE_DIR / "data"

def run(cmd: list, desc: str):
    print(f"\n{'='*60}")
    print(f"▶ {desc}")
    print(f"  $ {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=PIPELINE_DIR)
    if result.returncode != 0:
        print(f"❌ Falhou: {desc} (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"✅ OK: {desc}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline ENEM completo")
    parser.add_argument('--ano', type=int, default=2025)
    parser.add_argument('--cor', type=str, default='AZUL')
    parser.add_argument('--dia', type=int, default=1, choices=[1, 2])
    parser.add_argument('--skip-extract', action='store_true', help='Pula extração LLM (usa JSON existente)')
    parser.add_argument('--skip-etl', action='store_true', help='Pula ETL TRI (usa Parquet existente)')
    parser.add_argument('--skip-fuse', action='store_true', help='Pula fusão')
    parser.add_argument('--skip-load', action='store_true', help='Pula carga ArangoDB')
    args = parser.parse_args()
    
    ano = args.ano
    cor = args.cor.upper()
    dia = args.dia
    
    # Paths
    pdf_path = DATA_DIR.parent.parent / "arquivos_hd" / "Dados ENEM" / f"microdados_enem_{ano}" / f"microdados_enem_{ano}_defeso" / f"prova-{cor.lower()}-dia-{dia}-enem-{ano}.pdf"
    
    # Para 2025, o path é diferente
    if ano == 2025:
        pdf_path = Path("/home/gumentz/arquivos_hd/Dados ENEM/microdados_enem_2025/microdados_enem_2025_defeso/prova-azul-dia-1-enem-2025.pdf")
    
    extracted_json = DATA_DIR / "extracted" / str(ano) / f"{cor}_dia{dia}.json"
    tri_parquet = DATA_DIR / "tri" / f"itens_tri_{ano}.parquet"
    fused_jsonl = DATA_DIR / "fused" / f"questoes_enem_{ano}_{cor}_D{dia}.jsonl"
    
    print(f"📋 Pipeline ENEM {ano} - {cor} Dia {dia}")
    print(f"  PDF: {pdf_path}")
    print(f"  Extracted: {extracted_json}")
    print(f"  TRI: {tri_parquet}")
    print(f"  Fused: {fused_jsonl}")
    
    # 1. ETL TRI (pode rodar em paralelo com extração)
    if not args.skip_etl:
        run([
            sys.executable, str(SCRIPTS_DIR / "etl_tri.py")
        ], "ETL TRI - todos os anos")
    
    # 2. Extração Multimodal (LLM)
    if not args.skip_extract:
        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {pdf_path}")
            sys.exit(1)
        
        run([
            sys.executable, str(SCRIPTS_DIR / "extract_2025_test.py"),
            "--pdf", str(pdf_path),
            "--output", str(extracted_json)
        ], f"Extração LLM {ano} {cor} D{dia}")
    
    # 3. Fusão
    if not args.skip_fuse:
        run([
            sys.executable, str(SCRIPTS_DIR / "fuse.py"),
            "--ano", str(ano),
            "--cor", cor,
            "--dia", str(dia),
            "--llm", str(extracted_json),
            "--tri", str(tri_parquet),
            "--output", str(fused_jsonl)
        ], f"Fusão LLM+TRI {ano} {cor} D{dia}")
    
    # 4. Carga ArangoDB (opcional)
    if not args.skip_load:
        run([
            sys.executable, str(SCRIPTS_DIR / "load_arangodb.py"),
            "--input", str(fused_jsonl)
        ], f"Carga ArangoDB {ano} {cor} D{dia}")
    
    print(f"\n{'='*60}")
    print(f"🎉 Pipeline completo para {ano} {cor} Dia {dia}")
    print(f"   Documentos finais: {fused_jsonl}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()