#!/usr/bin/env python3
"""
Extração complementar para questões 15-38 (páginas 5-13)
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
Extraia APENAS as questões {questoes_alvo} destas imagens.
Retorne array com exatamente essas questões (posicao, enunciado, texto_base, alternativas A-E, metadados_visual).
Se uma questão não estiver nas imagens, NÃO a inclua.
"""

async def pdf_para_imagens(pdf_path: Path, output_dir: Path, dpi: int = 200) -> List[Path]:
    logger.info(f"Convertendo PDF (DPI={dpi})...")
    doc = fitz.open(str(pdf_path))
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_path = output_dir / f"page_{page_num+1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
    doc.close()
    return image_paths

@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extrair_foco(client: genai.Client, image_paths: List[Path], questoes_alvo: List[int]) -> list[dict]:
    uploaded_files = []
    for img_path in image_paths:
        f = client.files.upload(file=str(img_path))
        uploaded_files.append(f)
    
    try:
        prompt = PROMPT_FOCO.format(questoes_alvo=questoes_alvo)
        
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt] + uploaded_files,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GEMINI_SCHEMA,
                temperature=0.0,
                max_output_tokens=16384,
            )
        )
        
        logger.debug(f"Foco {questoes_alvo}: finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        
        if response.parsed is not None:
            return response.parsed
        if response.text:
            import json as json_module
            try:
                return json_module.loads(response.text)
            except Exception as e:
                logger.error(f"Parse falhou: {e}")
                logger.debug(f"Texto: {response.text[:500]}")
        return []
    finally:
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
            except Exception:
                pass

async def main():
    logger.add("/home/gumentz/enem-pipeline/logs/extract_15_38.log", rotation="10 MB")
    logger.info("=== EXTRAÇÃO FOCO: Questões 15-38 ===")
    
    image_paths = await pdf_para_imagens(PDF_PATH, IMAGES_DIR, dpi=200)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Questões 15-38 ≈ páginas 5-13 (3 questões/página)
    grupos = [
        (image_paths[4:6], [15, 16, 17]),      # páginas 5-6
        (image_paths[6:8], [18, 19, 20]),      # páginas 7-8
        (image_paths[8:10], [21, 22, 23]),     # páginas 9-10
        (image_paths[10:12], [24, 25, 26]),    # páginas 11-12
        (image_paths[12:14], [27, 28, 29]),    # páginas 13-14
        (image_paths[14:16], [30, 31, 32]),    # páginas 15-16
        (image_paths[16:18], [33, 34, 35]),    # páginas 17-18
        (image_paths[18:20], [36, 37, 38]),    # páginas 19-20
    ]
    
    todas_recuperadas = []
    
    for imgs, alvo in grupos:
        logger.info(f"Extraindo Q{alvo} das páginas {[image_paths.index(i)+1 for i in imgs]}")
        recuperadas = await extrair_foco(client, imgs, alvo)
        for q in recuperadas:
            if q.get('posicao') in alvo:
                todas_recuperadas.append(q)
                logger.success(f"  Recuperou Q{q['posicao']}")
    
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