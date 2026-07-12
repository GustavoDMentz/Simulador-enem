#!/usr/bin/env python3
"""
Batch process runner for Day 2 exams (2017 - 2025)
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path

BASE_DIR = Path("/home/gumentz/arquivos_hd/Dados ENEM")
PIPELINE_DIR = Path("/home/gumentz/enem-pipeline")

# Mapeamento de PDFs do Segundo Dia (AZUL, AMARELO, CINZA, ROSA)
# Gerado e validado a partir do escaneamento do HD
PDF_MAP = {
  2017: {
    "P1": {
      "AMARELO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/02_Domingo 12-11-17/ENEM_2017_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/02_Domingo 12-11-17/ENEM_2017_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/02_Domingo 12-11-17/ENEM_2017_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P1/02_Domingo 12-11-17/ENEM_2017_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 02/ENEM_2017_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 02/ENEM_2017_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 02/ENEM_2017_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2017/PROVAS E GABARITOS/PROVAS/P2/Dia 02/ENEM_2017_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2018: {
    "P1": {
      "AMARELO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2018/PROVAS E GABARITOS/ENEM_2018_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2019: {
    "P1": {
      "AMARELO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2019/PROVAS E GABARITOS/ENEM_2019_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2020: {
    "DIGITAL": {
      "AMARELO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_DIGITAL_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_DIGITAL_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_DIGITAL_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_DIGITAL_CAD_08_DIA_2_ROSA.pdf"
    },
    "P1": {
      "AMARELO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2020/PROVAS E GABARITOS/ENEM_2020_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2021: {
    "DIGITAL": {
      "AMARELO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_DIGITAL_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_DIGITAL_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_DIGITAL_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_DIGITAL_CAD_08_DIA_2_ROSA.pdf"
    },
    "P1": {
      "AMARELO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2021/PROVAS E GABARITOS/ENEM_2021_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2022: {
    "DIGITAL": {
      "AMARELO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_DIGITAL_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_DIGITAL_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_DIGITAL_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_DIGITAL_CAD_08_DIA_2_ROSA.pdf"
    },
    "P1": {
      "AMARELO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2022/PROVAS E GABARITOS/ENEM_2022_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2023: {
    "P1": {
      "AMARELO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P1_CAD_08_DIA_2_ROSA.pdf"
    },
    "P2": {
      "AMARELO": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_05_DIA_2_AMARELO.pdf",
      "AZUL": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_07_DIA_2_AZUL.pdf",
      "CINZA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_06_DIA_2_CINZA.pdf",
      "ROSA": "microdados_enem_2023/microdados_enem_2023 atualizado sem as logos/PROVAS E GABARITOS/ENEM_2023_P2_CAD_08_DIA_2_ROSA.pdf"
    }
  },
  2024: {
    "P1": {
      "AZUL": "microdados_enem_2024/microdados_enem_2024_defeso/caderno-2-dia-azul-enem-2024.pdf"
    }
  },
  2025: {
    "P1": {
      "AZUL": "microdados_enem_2025/microdados_enem_2025_defeso/enem-2025-2-dia-caderno-azul.pdf"
    }
  }
}

async def extract_pdf(year: int, prova: str, cor: str, pdf_rel: str) -> bool:
    """Extrai um PDF específico do dia 2 usando o script de extração."""
    pdf_path = BASE_DIR / pdf_rel
    if not pdf_path.exists():
        print(f"  ❌ PDF não encontrado: {pdf_path}")
        return False
    
    output_dir = PIPELINE_DIR / "data" / "extracted" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{cor}_dia2.json"
    
    if output_file.exists():
        print(f"  ⏭️  Extração já existe para {year} {prova} {cor} Dia 2 (pulando)")
        return True
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "extract_generic.py"),
        "--pdf", str(pdf_path),
        "--ano", str(year),
        "--cor", cor,
        "--dia", "2"
    ]
    
    print(f"  🔄 Extraindo {year} {prova} {cor} Dia 2...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    
    if result.returncode == 0:
        print(f"  ✅ {year} {prova} {cor} Dia 2 → {output_file}")
        return True
    else:
        print(f"  ❌ Falha extração: {result.stderr[:500]}")
        return False

async def run_fusion(year: int, prova: str, cor: str) -> bool:
    """Roda a fusão LLM + TRI."""
    extracted = PIPELINE_DIR / "data" / "extracted" / str(year) / f"{cor}_dia2.json"
    tri_parquet = PIPELINE_DIR / "data" / "tri" / "itens_tri_todos_anos.parquet"
    output = PIPELINE_DIR / "data" / "fused" / f"questoes_enem_{year}_{cor}_D2.jsonl"
    
    if output.exists():
        print(f"  ⏭️  Fusão já existe para {year} {prova} {cor} Dia 2 (pulando)")
        return True
    
    if not extracted.exists():
        print(f"  ❌ Extração não encontrada: {extracted}")
        return False
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "fuse.py"),
        "--ano", str(year),
        "--cor", cor,
        "--dia", "2",
        "--llm", str(extracted),
        "--tri", str(tri_parquet),
        "--output", str(output)
    ]
    
    print(f"  🔗 Fundindo {year} {prova} {cor} Dia 2...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(f"  ✅ Fusão {year} {prova} {cor} Dia 2 → {output}")
        return True
    else:
        print(f"  ❌ Fusão falhou: {result.stderr[:500]}")
        return False

async def load_arango(year: int, prova: str, cor: str) -> bool:
    """Carrega no ArangoDB."""
    fused = PIPELINE_DIR / "data" / "fused" / f"questoes_enem_{year}_{cor}_D2.jsonl"
    if not fused.exists():
        print(f"  ❌ Fusão não encontrada: {fused}")
        return False
    
    cmd = [
        sys.executable, str(PIPELINE_DIR / "scripts" / "load_arangodb_http.py"),
        "--input", str(fused)
    ]
    
    print(f"  📥 Carregando {year} {prova} {cor} Dia 2 no ArangoDB...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        print(f"  ✅ Carregado {year} {prova} {cor} Dia 2")
        return True
    else:
        print(f"  ❌ Carga falhou: {result.stderr[:500]}")
        return False

async def process_year(year: int):
    """Processa todos os PDFs de um ano para o segundo dia."""
    print(f"\n{'='*60}")
    print(f"📅 PROCESSANDO SEGUNDO DIA - ANO {year}")
    print(f"{'='*60}")
    
    if year not in PDF_MAP:
        print(f"  ⚠️  Ano {year} não mapeado no Dia 2")
        return
        
    ano_map = PDF_MAP[year]
    sucessos_extracao = 0
    total_extracao = 0
    
    # 1. Extração
    print(f"\n📄 ETAPA 1: Extração Multimodal (Dia 2)")
    for prova in sorted(ano_map.keys()):
        for cor in sorted(ano_map[prova].keys()):
            pdf_rel = ano_map[prova][cor]
            total_extracao += 1
            if await extract_pdf(year, prova, cor, pdf_rel):
                sucessos_extracao += 1
            await asyncio.sleep(2)
            
    print(f"\n📊 Extração Dia 2: {sucessos_extracao}/{total_extracao} sucessos")
    
    # 2. Fusão
    print(f"\n🔗 ETAPA 2: Fusão LLM + TRI (Dia 2)")
    sucessos_fusao = 0
    total_fusao = 0
    for prova in sorted(ano_map.keys()):
        for cor in sorted(ano_map[prova].keys()):
            total_fusao += 1
            if await run_fusion(year, prova, cor):
                sucessos_fusao += 1
            await asyncio.sleep(1)
            
    print(f"\n📊 Fusão Dia 2: {sucessos_fusao}/{total_fusao} sucessos")
    
    # 3. Carga ArangoDB
    print(f"\n📥 ETAPA 3: Carga ArangoDB (Dia 2)")
    sucessos_carga = 0
    total_carga = 0
    for prova in sorted(ano_map.keys()):
        for cor in sorted(ano_map[prova].keys()):
            total_carga += 1
            if await load_arango(year, prova, cor):
                sucessos_carga += 1
            await asyncio.sleep(1)
            
    print(f"\n📊 Carga Dia 2: {sucessos_carga}/{total_carga} sucessos")

async def main():
    print("🚀 PIPELINE ENEM - SEGUNDO DIA (2017-2025)")
    print("="*60)
    
    resultados = []
    # Processa de 2017 a 2025
    for year in range(2017, 2026):
        try:
            await process_year(year)
        except Exception as e:
            print(f"❌ Erro no ano {year} (Dia 2): {e}")

if __name__ == "__main__":
    asyncio.run(main())
