#!/usr/bin/env python3
"""
Extração multimodal ENEM - versão direta com PDF upload + schema fix
"""

import os
import json
import asyncio
import sys
from pathlib import Path
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada")

SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "posicao": types.Schema(type=types.Type.INTEGER),
            "enunciado": types.Schema(type=types.Type.STRING),
            "texto_base": types.Schema(type=types.Type.STRING),
            "alternativas": types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "A": types.Schema(type=types.Type.STRING),
                    "B": types.Schema(type=types.Type.STRING),
                    "C": types.Schema(type=types.Type.STRING),
                    "D": types.Schema(type=types.Type.STRING),
                    "E": types.Schema(type=types.Type.STRING),
                },
                required=["A", "B", "C", "D", "E"],
            ),
            "metadados_visual": types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "contem_imagem": types.Schema(type=types.Type.BOOL),
                    "descricao_imagem": types.Schema(type=types.Type.STRING),
                },
                required=["contem_imagem"],
            ),
        },
        required=["posicao", "enunciado", "alternativas", "metadados_visual"],
    )
)

PROMPT = """
Extraia TODAS as 90 questões deste caderno ENEM na ordem física.
Para cada questão retorne JSON com:
- posicao: número da questão (1-90)
- enunciado: texto completo da pergunta
- texto_base: texto de apoio (poemas, gráficos, textos) ou string vazia
- alternativas: objeto com chaves A, B, C, D, E e textos completos
- metadados_visual: {contem_imagem: true/false, descricao_imagem: "descrição detalhada"}

REGRAS: Extraia EXATAMENTE o que está no PDF. Mantenha formatação original. Se houver imagem/gráfico/tabela, descreva-a detalhadamente.
"""

@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extract_pdf_direct(client: genai.Client, pdf_path: Path) -> list[dict]:
    """Upload PDF directly and extract all questions at once."""
    pdf_file = client.files.upload(file=str(pdf_path))
    logger.info(f"Uploaded: {pdf_file.name}")
    
    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT, pdf_file],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
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
                },
                temperature=0.0,
                max_output_tokens=32768,
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
        try: client.files.delete(name=pdf_file.name)
        except: pass

async def main(pdf: str, year: int, color: str, day: int):
    import os, json
    from pathlib import Path
    from loguru import logger
    
    logger.add(f"/home/gumentz/enem-pipeline/logs/extract_direct_{color}_dia{day}.log", rotation="10 MB")
    logger.info(f"=== Direct PDF extraction ===")
    
    pdf_path = Path(pdf)
    out_file = Path(f"/home/gumentz/enem-pipeline/data/extracted/{year}/{color}_dia{day}.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    questions = await extract_pdf_direct(genai.Client(api_key=os.getenv("GEMINI_API_KEY")), Path(pdf))
    
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(questions, ensure_ascii=False, indent=2))
    logger.success(f"Saved {len(questions)} questions to {out_file}")

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--cor", required=True)
    parser.add_argument("--dia", type=int, required=True)
    args = parser.parse_args()
    
    import asyncio
    asyncio.run(main(args.pdf, args.ano, args.cor, args.dia))