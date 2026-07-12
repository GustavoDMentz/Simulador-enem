#!/usr/bin/env python3
"""
Extração multimodal ENEM - versão otimizada para processamento em lote
"""

import os
import json
import asyncio
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from dotenv import load_dotenv
import fitz

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada")

# Schema
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
                "properties": {"A": {"type": "string"}, "B": {"type": "string"}, "C": {"type": "string"}, "D": {"type": "string"}, "E": {"type": "string"}},
                "required": ["A", "B", "C", "D", "E"]
            },
            "metadados_visual": {
                "type": "object",
                "properties": {"contem_imagem": {"type": "boolean"}, "descricao_imagem": {"type": "string"}},
                "required": ["contem_imagem"]
            }
        },
        "required": ["posicao", "enunciado", "alternativas", "metadados_visual"]
    }
}

PROMPT = """
Extraia TODAS as questões visíveis nestas páginas do ENEM.
Para cada questão: posicao, enunciado, texto_base, alternativas (A-E), metadados_visual (contem_imagem, descricao_imagem).
Ordem deve corresponder à ordem física no caderno.
"""

@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extract_batch(client: genai.Client, images: list[Path], start_pos: int) -> list[dict]:
    uploaded = []
    for img in images:
        f = client.files.upload(file=str(img))
        uploaded.append(f)
    
    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT + f"\n\nPáginas sequenciais. Primeira questão ~#{start_pos}."] + uploaded,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={"type": "array", "items": {"type": "object"}},
                temperature=0.0,
                max_output_tokens=16384,
            )
        )
        
        if resp.parsed:
            return resp.parsed
        if resp.text:
            try:
                return json.loads(resp.text)
            except:
                return []
        return []
    finally:
        for f in uploaded:
            try: client.files.delete(name=f.name)
            except: pass

async def pdf_to_images(pdf: Path, out_dir: Path, dpi=150) -> list[Path]:
    doc = fitz.open(str(pdf))
    out = []
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=mat)
        p = out_dir / f"p{i+1:03d}.png"
        pix.save(str(p))
        out.append(p)
    doc.close()
    return out

async def extract_pdf(pdf_path: Path, out_file: Path, max_q=90):
    logger.info(f"Processing {pdf_path.name}")
    images_dir = Path("/tmp") / "enem_images" / pdf_path.stem
    images_dir.mkdir(parents=True, exist_ok=True)
    
    images = await pdf_to_images(pdf_path, images_dir, dpi=150)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # First pass: 2 pages per batch (~6 questions)
    all_q = []
    BATCH = 2
    for i in range(0, len(images), 2):
        batch = images[i:i+2]
        q = await extract_batch(genai.Client(api_key=os.getenv("GEMINI_API_KEY")), images[i:i+2], i+1)
        all_q.extend(q)
        logger.info(f"Batch {i//2+1}: {len(q)} questions")
        await asyncio.sleep(1)
    
    # Deduplicate
    seen = set()
    uniq = []
    for q in sorted(all_q, key=lambda x: x.get('posicao', 0)):
        pos = q.get('posicao')
        if pos and pos not in seen:
            seen.add(pos)
            uniq.append(q)
    
    # Gap fill if needed
    found = {q['posicao'] for q in uniq if q.get('posicao')}
    missing = set(range(1, 91)) - found
    if missing:
        logger.warning(f"Missing {len(missing)} questions: {sorted(missing)[:10]}...")
    
    # Validate
    valid = []
    for i, q in enumerate(uniq):
        if q.get('posicao') and q.get('enunciado') and q.get('alternativas'):
            valid.append(q)
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(uniq, ensure_ascii=False, indent=2))
    logger.success(f"Saved {len(uniq)} questions to {out_file}")
    return uniq

async def main(pdf: str, year: int, color: str, day: int):
    pdf_path = Path(pdf)
    out_dir = Path(f"/home/gumentz/enem-pipeline/data/extracted/{year}")
    out_file = out_dir / f"{color}_dia{day}.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(f"/home/gumentz/enem-pipeline/logs/extract_{year}_{color}_dia{day}.log", rotation="10 MB")
    logger.info(f"=== {pdf} -> {out_file} ===")
    
    await extract_pdf(Path(pdf), Path(f"/home/gumentz/enem-pipeline/data/extracted/{year}/{color}_dia{day}.json"))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--cor", required=True)
    parser.add_argument("--dia", type=int, required=True)
    args = parser.parse_args()
    
    asyncio.run(extract_pdf(Path(args.pdf), Path(f"/home/gumentz/enem-pipeline/data/extracted/{args.ano}/{args.cor}_dia{args.dia}.json")))