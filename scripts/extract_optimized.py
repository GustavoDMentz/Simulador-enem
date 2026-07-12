#!/usr/bin/env python3
"""
Extração ENEM otimizada - lotes de 2 páginas (~6 questões)
"""

import os, json, asyncio, sys, fitz, os
from pathlib import Path
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada")

SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "posicao": {"type": "integer"},
            "enunciado": {"type": "string"},
            "texto_base": {"type": "string"},
            "alternativas": {"type": "object", "properties": {"A": {"type": "string"}, "B": {"type": "string"}, "C": {"type": "string"}, "D": {"type": "string"}, "E": {"type": "string"}}, "required": ["A", "B", "C", "D", "E"]},
            "metadados_visual": {"type": "object", "properties": {"contem_imagem": {"type": "boolean"}, "descricao_imagem": {"type": "string"}}, "required": ["contem_imagem"]}
        },
        "required": ["posicao", "enunciado", "alternativas", "metadados_visual"]
    }
}

PROMPT = """Extraia TODAS as questões visíveis nestas páginas do ENEM.
Para cada: posicao, enunciado, texto_base, alternativas (A-E), metadados_visual (contem_imagem, descricao_imagem)."""

async def pdf_to_images(pdf_path: Path, out_dir: Path, dpi=150) -> list:
    doc = fitz.open(str(pdf_path))
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

@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extract_batch(client, images: list, start_q: int) -> list:
    uploaded = [client.files.upload(file=str(img)) for img in images]
    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[f"Extraia questões começando ~#{start_q}:", *[f for f in uploaded]],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=16384,
            )
        )
        return resp.parsed if resp.parsed else (json.loads(resp.text) if resp.text else [])
    finally:
        for f in uploaded:
            try: client.files.delete(name=f.name)
            except: pass

async def pdf_to_images(pdf_path: Path, out_dir: Path, dpi=150) -> list:
    doc = fitz.open(str(pdf_path))
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

async def process_pdf(pdf_path: Path, year: int, color: str, day: int):
    logger.add(f"/home/gumentz/enem-pipeline/logs/extract_{year}_{color}_dia{day}.log", rotation="10 MB")
    logger.info(f"Processing {pdf_path.name}")
    
    images_dir = Path(f"/home/gumentz/enem-pipeline/data/extracted/{year}/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    images = await pdf_to_images(Path(pdf_path), images_dir, dpi=150)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # 2 pages per batch = ~6 questions
    all_q = []
    for i in range(0, len(images), 2):
        batch = images[i:i+2]
        q = await extract_batch(genai.Client(api_key=os.getenv("GEMINI_API_KEY")), batch, i+1)
        logger.info(f"Batch {i//2+1}: {len(q)} questions")
        all_q.extend(q)
        await asyncio.sleep(1)
    
    # Deduplicate
    seen = set()
    uniq = []
    for q in sorted(all_q, key=lambda x: x.get('posicao', 0)):
        pos = q.get('posicao')
        if pos and pos not in seen:
            seen.add(pos)
            uniq.append(q)
    
    # Save
    out_file = Path(f"/home/gumentz/enem-pipeline/data/extracted/{year}/{color}_dia{day}.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(uniq, ensure_ascii=False, indent=2))
    logger.success(f"Saved {len(uniq)} questions")
    return uniq

async def main(pdf: str, year: int, color: str, day: int):
    await process_pdf(Path(pdf), year, color, day)

if __name__ == "__main__":
    import argparse, os, json, fitz
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--cor", required=True)
    parser.add_argument("--dia", type=int, required=True)
    args = parser.parse_args()
    
    asyncio.run(main(args.pdf, args.ano, args.cor, args.dia))