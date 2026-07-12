#!/usr/bin/env python3
"""
Batch processor for ENEM 2017-2024
Processes all available PDFs through the extraction + TRI fusion pipeline
"""

import os
import json
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

BASE_DIR = Path("/home/gumentz/arquivos_hd/Dados ENEM")
PIPELINE_DIR = Path("/home/gumentz/enem-pipeline")

# Mapeamento de PDFs por ano (cores padrão exceto 2024/2025 que só têm AZUL)
PDF_MAP = {
    2017: {
        "P1": {
            "AZUL": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/01_Domingo 05-11-17/ENEM_2017_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/01_Domingo 05-11-17/ENEM_2017_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/01_Domingo 05-11-17/ENEM_2017_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/01_Domingo 05-11-17/ENEM_2017_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 01/ENEM_2017_P2_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 01/ENEM_2017_P2_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 01/ENEM_2017_P2_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 01/ENEM_2017_P2_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2018: {
        "P1": {
            "AZUL": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_07_DIA_2_AZUL.pdf",
            "AMARELO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_05_DIA_2_AMARELO.pdf",
            "BRANCO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2019: {
        "P1": {
            "AZUL": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2020: {
        "P1": {
            "AZUL": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P2_CAD_07_DIA_2_AZUL.pdf",
            "AMARELO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_05_DIA_2_AMARELO.pdf",
            "BRANCO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2021: {
        "P1": {
            "AZUL": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2022: {
        "P1": {
            "AZUL": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_04_DIA_1_ROSA.pdf",
        }
    },
    2023: {
        "P1": {
            "AZUL": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_01_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_02_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_03_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_04_DIA_1_ROSA.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_1_DIA_1_AZUL.pdf",
            "AMARELO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_2_DIA_1_AMARELO.pdf",
            "BRANCO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_3_DIA_1_BRANCO.pdf",
            "ROSA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_4_DIA_1_ROSA.pdf",
        }
    },
    2024: {
        "P1": {
            "AZUL": "microdados_enem_2024/microdados_enem_2024_defeso/caderno-1-dia-azul-enem-2024.pdf",
        },
        "P2": {
            "AZUL": "microdados_enem_2024/microdados_enem_2024_defeso/caderno-2-dia-azul-enem-2024.pdf",
        }
    },
}

# Mapeamento P1/P2 -> dia
PROVA_DIA = {"P1": 1, "P2": 2}

# Mapeamento cor para nome normalizado
COR_MAP = {
    "AZUL": "AZUL", "AMARELO": "AMARELO", "BRANCO": "BRANCO", "ROSA": "ROSA",
    "VERDE": "VERDE", "CINZA": "CINZA", "LARANJA": "LARANJA", "LILAS": "LILAS",
}

async def extract_pdf(year: int, prova: str, cor: str, pdf_rel: str) -> bool:
    """Extrai um PDF específico usando o script de extração."""
    pdf_path = BASE_DIR / pdf_rel
    if not pdf_path.exists():
        print(f"  ❌ PDF não encontrado: {pdf_path}")
        return False
    
    output_dir = PIPELINE_DIR / "data" / "extracted" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{cor}_dia{PROVA_DIA[prova]}.json"
    
    if output_file.exists():
        print(f"  ⏭️  Extração já existe para {year} {prova} {cor} (pulando)")
        return True
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "extract_generic.py"),
        "--pdf", str(pdf_path),
        "--ano", str(year),
        "--cor", cor,
        "--dia", str(PROVA_DIA[prova])
    ]
    
    print(f"  🔄 Extraindo {year} {prova} {cor}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    
    if result.returncode == 0:
        print(f"  ✅ {year} {prova} {cor} → {output_file}")
        return True
    else:
        print(f"  ❌ Falha: {result.stderr[:500]}")
        return False
 
async def run_fusion(year: int, prova: str, cor: str) -> bool:
    """Roda a fusão LLM + TRI."""
    extracted = PIPELINE_DIR / "data" / "extracted" / str(year) / f"{cor}_dia{PROVA_DIA[prova]}.json"
    tri_parquet = PIPELINE_DIR / "data" / "tri" / "itens_tri_todos_anos.parquet"
    output = PIPELINE_DIR / "data" / "fused" / f"questoes_enem_{year}_{cor}_D{PROVA_DIA[prova]}.jsonl"
    
    if output.exists():
        print(f"  ⏭️  Fusão já existe para {year} {prova} {cor} (pulando)")
        return True
    
    if not extracted.exists():
        print(f"  ❌ Extração não encontrada: {extracted}")
        return False
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "fuse.py"),
        "--ano", str(year),
        "--cor", cor,
        "--dia", str(PROVA_DIA[prova]),
        "--llm", str(extracted),
        "--tri", str(tri_parquet),
        "--output", str(output)
    ]
    
    print(f"  🔗 Fundindo {year} {prova} {cor}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(f"  ✅ Fusão {year} {prova} {cor} → {output}")
        return True
    else:
        print(f"  ❌ Fusão falhou: {result.stderr[:500]}")
        return False

async def load_arango(year: int, prova: str, cor: str) -> bool:
    """Carrega no ArangoDB."""
    fused = PIPELINE_DIR / "data" / "fused" / f"questoes_enem_{year}_{cor}_D{PROVA_DIA[prova]}.jsonl"
    if not fused.exists():
        print(f"  ❌ Fusão não encontrada: {fused}")
        return False
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "load_arangodb_http.py"),
        "--input", str(fused)
    ]
    
    print(f"  📥 Carregando {year} {prova} {cor} no ArangoDB...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(f"  ✅ Carregado {year} {prova} {cor}")
        return True
    else:
        print(f"  ❌ Carga falhou: {result.stderr[:500]}")
        return False

async def process_year(year: int):
    """Processa todos os PDFs de um ano."""
    print(f"\n{'='*60}")
    print(f"📅 PROCESSANDO ANO {year}")
    print(f"{'='*60}")
    
    if year not in PDF_MAP:
        print(f"  ⚠️  Ano {year} não mapeado")
        return
    
    ano_map = PDF_MAP[year]
    sucessos_extracao = 0
    total_extracao = 0
    
    # 1. Extração
    print(f"\n📄 ETAPA 1: Extração Multimodal")
    for prova in ["P1", "P2"]:
        if prova not in ano_map:
            continue
        for cor in ano_map[prova]:
            pdf_rel = ano_map[prova][cor]
            total_extracao += 1
            if await extract_pdf(year, prova, cor, pdf_rel):
                sucessos_extracao += 1
            await asyncio.sleep(2)  # Rate limit
    
    print(f"\n📊 Extração: {sucessos_extracao}/{total_extracao} sucessos")
    
    # 2. Fusão
    print(f"\n🔗 ETAPA 2: Fusão LLM + TRI")
    sucessos_fusao = 0
    total_fusao = 0
    for prova in ["P1", "P2"]:
        if prova not in ano_map:
            continue
        for cor in ano_map[prova]:
            total_fusao += 1
            if await run_fusion(year, prova, COR_MAP.get(cor, cor)):
                sucessos_fusao += 1
            await asyncio.sleep(1)
    
    print(f"\n📊 Fusão: {sucessos_fusao}/{total_fusao} sucessos")
    
    # 3. Carga ArangoDB
    print(f"\n📥 ETAPA 3: Carga ArangoDB")
    sucessos_carga = 0
    total_carga = 0
    for prova in ["P1", "P2"]:
        if prova not in ano_map:
            continue
        for cor in ano_map[prova]:
            total_carga += 1
            cor_norm = COR_MAP.get(cor, cor)
            if await load_arango(year, prova, cor):
                sucessos_carga += 1
            await asyncio.sleep(1)
    
    print(f"\n📊 Carga: {sucessos_carga}/{total_carga} sucessos")
    
    return {
        "ano": year,
        "extracao": f"{sucessos_extracao}/{total_extracao}",
        "fusao": f"{sucessos_fusao}/{total_fusao}",
        "carga": f"{sucessos_carga}/{total_carga}"
    }

async def main():
    print("🚀 PIPELINE ENEM 2017-2024")
    print("="*60)
    
    resultados = []
    for year in range(2017, 2025):
        try:
            resultado = await process_year(year)
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Erro no ano {year}: {e}")
            resultados.append({"ano": year, "erro": str(e)})
    
    # Resumo final
    print("\n" + "="*60)
    print("📋 RESUMO FINAL")
    print("="*60)
    for r in resultados:
        if "erro" in r:
            print(f"  {r['ano']}: ❌ ERRO - {r['erro']}")
        else:
            print(f"  {r['ano']}: Extração={r['extracao']} | Fusão={r['fusao']} | Carga={r['carga']}")

if __name__ == "__main__":
    asyncio.run(main())