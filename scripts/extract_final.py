#!/usr/bin/env python3
"""
Extração final para questões 15-20, 23, 35 - lotes de 1 página, DPI 150
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from dotenv import load_dotenv
import fitz

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada.")

PDF_PATH = Path("/home/gumentz/arquivos_hd/Dados ENEM/microdados_enem_2025/microdados_enem_2025_defeso/prova-azul-dia-1-enem-2025.pdf")
OUTPUT_DIR = Path("/home/gumentz/enem-pipeline/data/extracted/2025")
IMAGES_DIR = OUTPUT_DIR / "images"
OUTPUT_FILE = OUTPUT_DIR / "AZUL_dia1.json"

GEMINI_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "posicao": {"type": "integer"},
            "enunciado": {"type": "string"},
            "texto_base": {"type": "string"},
            "alternativas": {
                "type": "object",
                "properties": {
                    "A": {"type": "string"}, "B": {"type": "string"},
                    "C": {"type": "string"}, "D": {"type": "string"}, "E": {"type": "string"},
                },
                "required": ["A", "B", "C", "D", "E"]
            },
            "metadados_visual": {
                "type": "object",
                "properties": {
                    "contem_imagem": {"type": "boolean"},
                    "descricao_imagem": {"type": "string"},
                },
                "required": ["contem_imagem"]
            }
        },
        "required": ["posicao", "enunciado", "alternativas", "metadados_visual"]
    }
}

PROMPT_FOCO = """
Extraia APENAS a questão {pos} desta imagem.
Retorne array com exatamente esta questão (posicao, enunciado, texto_base, alternativas A-E, metadados_visual).
Se não estiver na imagem, retorne array vazio.
"""

async def pdf_para_imagens(pdf_path: Path, output_dir: Path, dpi: int = 150) -> List[Path]:
    logger.info(f"Convertendo PDF (DPI={dpi})...")
    doc = fitz.open(str(pdf_path))
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_path = output_dir / f"page_{page_num+1:03d}_dpi150.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths

@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extrair_uma(client: genai.Client, image_path: Path, pos: int) -> list[dict]:
    f = client.files.upload(file=str(image_path))
    try:
        prompt = PROMPT_FOCO.format(pos=pos)
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, f],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GEMINI_SCHEMA,
                temperature=0.0,
                max_output_tokens=8192,
            )
        )
        logger.debug(f"Q{pos}: finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        if response.parsed is not None:
            return response.parsed
        if response.text:
            import json as json_module
            try:
                return json_module.loads(response.text)
            except Exception as e:
                logger.error(f"Parse Q{pos}: {e}")
        return []
    finally:
        try:
            client.files.delete(name=f.name)
        except Exception:
            pass

async def main():
    logger.add("/home/gumentz/enem-pipeline/logs/extract_final.log", rotation="10 MB")
    logger.info("=== EXTRAÇÃO FINAL: 15-20, 23, 35 (1 página cada) ===")
    
    image_paths = await pdf_para_imagens(PDF_PATH, IMAGES_DIR, dpi=150)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Q15=pg5, Q16=pg6, Q17=pg6, Q18=pg7, Q19=pg7, Q20=pg8, Q23=pg8, Q35=pg12
    questoes_paginas = {
        15: 5, 16: 6, 17: 6, 18: 7, 19: 7, 20: 8, 23: 8, 35: 12
    }
    
    todas_recuperadas = []
    
    for pos, pg in questoes_paginas.items():
        logger.info(f"Extraindo Q{pos} da página {pg}...")
        img = image_paths[pg - 1]  # 0-indexed
        recuperadas = await extrair_uma(client, img, pos)
        for q in recuperadas:
            if q.get('posicao') == pos:
                todas_recuperadas.append(q)
                logger.success(f"  Recuperou Q{pos}")
    
    # Carrega extração principal
    with open(OUTPUT_FILE, 'r') as f:
        principais = json.load(f)
    
    # Merge
    pos_principais = {q['posicao'] for q in principais}
    for q in todas_recuperadas:
        if q.get('posicao') not in pos_principais:
            principais.append(q)
    
    principais.sort(key=lambda x: x.get('posicao', 0))
    
    # Salva
    OUTPUT_FILE.write_text(json.dumps(principais, ensure_ascii=False, indent=2))
    logger.success(f"✅ Total final: {len(principais)} questões")
    logger.info(f"Posições: {sorted(q['posicao'] for q in principais)}")

if __name__ == "__main__":
    try:
        import fitz
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "pymupdf", "--break-system-packages", "-q"], check=True)
        import fitz
    asyncio.run(main())