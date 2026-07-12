#!/usr/bin/env python3
"""
Extração final - lotes de 2 páginas (6 questões) para as faltando
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List
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

PROMPT_BATCH = """
Extraia APENAS as questões {questoes_alvo} destas imagens.
As imagens correspondem a páginas sequenciais do caderno ENEM 2025 AZUL Dia 1.

Retorne array JSON com exatamente estas questões (posicao, enunciado, texto_base, alternativas A-E, metadados_visual).
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
async def extrair_lote(client: genai.Client, image_paths: List[Path], questoes_alvo: List[int]) -> list[dict]:
    uploaded_files = []
    for img_path in image_paths:
        f = client.files.upload(file=str(img_path))
        uploaded_files.append(f)
    
    try:
        prompt = PROMPT_BATCH.format(questoes_alvo=questoes_alvo)
        
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
        
        logger.debug(f"Lote {questoes_alvo}: finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        
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
    logger.add("/home/gumentz/enem-pipeline/logs/extract_batch_final.log", rotation="10 MB")
    logger.info("=== EXTRAÇÃO FINAL: Lotes de 2 páginas ===")
    
    image_paths = await pdf_para_imagens(PDF_PATH, IMAGES_DIR, dpi=200)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Questões faltando: 15-20, 23, 35
    # Mapeamento: Q15-16=pg5-6, Q17-18=pg6-7, Q19-20=pg7-8, Q23=pg8-9, Q35=pg12-13
    lotes = [
        (image_paths[4:6], [15, 16]),      # páginas 5-6
        (image_paths[5:7], [17, 18]),      # páginas 6-7
        (image_paths[6:8], [19, 20]),      # páginas 7-8
        (image_paths[7:9], [23]),          # páginas 8-9
        (image_paths[11:13], [35]),        # páginas 12-13
    ]
    
    todas_recuperadas = []
    
    for imgs, alvo in lotes:
        logger.info(f"Extraindo Q{alvo} das páginas {[image_paths.index(i)+1 for i in imgs]}")
        recuperadas = await extrair_lote(client, imgs, alvo)
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