#!/usr/bin/env python3
"""
Extração multimodal ENEM 2025 - Prova AZUL Dia 1
Estratégia duas passagens:
  1. PASSAGEM PRINCIPAL: lotes 4 páginas, max_tokens=16384, temp=0
  2. PASSAGEM COMPLEMENTAR: identifica gaps (questões faltando) e reprocessa apenas essas páginas
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Set
from pydantic import BaseModel, Field
from enum import Enum
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from dotenv import load_dotenv
import fitz  # pymupdf

# ─── Config ──────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não encontrada. Defina no .env ou export.")

PDF_PATH = Path("/home/gumentz/arquivos_hd/Dados ENEM/microdados_enem_2025/microdados_enem_2025_defeso/prova-azul-dia-1-enem-2025.pdf")
OUTPUT_DIR = Path("/home/gumentz/enem-pipeline/data/extracted/2025")
IMAGES_DIR = OUTPUT_DIR / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "AZUL_dia1.json"

# ─── Schema Pydantic ─────────────────────────────────────────────────────
class Alternativas(BaseModel):
    A: str
    B: str
    C: str
    D: str
    E: str

class MetadadosVisual(BaseModel):
    contem_imagem: bool
    descricao_imagem: Optional[str] = None

class QuestaoExtraida(BaseModel):
    posicao: int = Field(ge=1, le=90)
    enunciado: str
    texto_base: str = ""
    alternativas: Alternativas
    metadados_visual: MetadadosVisual

# Schema para Gemini
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

PROMPT_EXTRACAO = """
Você é um extrator especializado em provas do ENEM. Receberá IMAGENS de páginas de um caderno de prova AZUL, Dia 1.

Extraia TODAS as questões visíveis nestas imagens na ordem em que aparecem.

Para cada questão, retorne EXATAMENTE:
1. posicao: número da questão no caderno
2. enunciado: texto completo da pergunta/comando
3. texto_base: texto de apoio (textos, poemas, gráficos, tabelas, charges) — vazio se não houver
4. alternativas: objeto com chaves A, B, C, D, E e textos completos
5. metadados_visual:
   - contem_imagem: true se a questão tiver imagem, gráfico, tabela, figura, charge, mapa
   - descricao_imagem: descrição textual do que a imagem mostra

REGRAS CRÍTICAS:
- Extraia EXATAMENTE o que está nas imagens. Não complete, não interprete.
- Mantenha formatação original (quebras de linha, maiúsculas, pontuação).
- Se questão continua na próxima imagem, extraia o que puder e marque na descricao_imagem.
- A ordem no JSON DEVE corresponder à ordem física no caderno.
"""

# ─── Conversão PDF → Imagens ─────────────────────────────────────────────
def pdf_para_imagens(pdf_path: Path, output_dir: Path, dpi: int = 200) -> List[Path]:
    logger.info(f"Convertendo PDF para imagens (DPI={dpi})...")
    doc = fitz.open(str(pdf_path))
    image_paths = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        
        img_path = output_dir / f"page_{page_num+1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)
        
        if (page_num + 1) % 10 == 0:
            logger.info(f"  {page_num+1}/{len(doc)} páginas convertidas")
    
    doc.close()
    logger.success(f"PDF convertido: {len(image_paths)} imagens em {output_dir}")
    return image_paths

# ─── Extrator por Lote (Passagem Principal) ──────────────────────────────
@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extrair_lote_principal(client: genai.Client, image_paths: List[Path], inicio_pos: int) -> list[dict]:
    """Extrai questões de um lote de imagens (configuração otimizada para throughput)."""
    uploaded_files = []
    for img_path in image_paths:
        f = client.files.upload(file=str(img_path))
        uploaded_files.append(f)
        logger.debug(f"  Upload: {img_path.name} -> {f.name}")
    
    try:
        prompt = f"{PROMPT_EXTRACAO}\n\nAs imagens correspondem a páginas sequenciais. A primeira questão esperada é aproximadamente a #{inicio_pos}."
        
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt] + uploaded_files,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GEMINI_SCHEMA,
                temperature=0.0,
                max_output_tokens=16384,  # Máximo permitido
            )
        )
        
        logger.debug(f"Lote {inicio_pos}: finish_reason={response.candidates[0].finish_reason if response.candidates else 'N/A'}")
        
        if response.parsed is not None:
            return response.parsed
        
        if response.text:
            import json as json_module
            try:
                return json_module.loads(response.text)
            except Exception as e:
                logger.error(f"Falha parse manual: {e}")
                logger.debug(f"Primeiros 500 chars: {response.text[:500]}")
        
        return []
        
    finally:
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
            except Exception:
                pass

# ─── Extrator Complementar (para gaps) ───────────────────────────────────
@retry(wait=wait_exponential(multiplier=2, min=10, max=120), stop=stop_after_attempt(3))
async def extrair_lote_complementar(client: genai.Client, image_paths: List[Path], questoes_alvo: List[int]) -> list[dict]:
    """Reprocessa páginas específicas para questões que faltaram."""
    uploaded_files = []
    for img_path in image_paths:
        f = client.files.upload(file=str(img_path))
        uploaded_files.append(f)
    
    try:
        prompt = f"""{PROMPT_EXTRACAO}

IMPORTANTE: Foque APENAS nas questões {min(questoes_alvo)}-{max(questoes_alvo)}. 
Extraia com máxima atenção, pois tentativas anteriores falharam nestas questões.
Se a questão não estiver nestas páginas, retorne array vazio para ela."""
        
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt] + uploaded_files,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GEMINI_SCHEMA,
                temperature=0.1,  # Leve criatividade para completar
                max_output_tokens=16384,
            )
        )
        
        if response.parsed is not None:
            return response.parsed
        if response.text:
            import json as json_module
            try:
                return json_module.loads(response.text)
            except Exception:
                pass
        return []
    finally:
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
            except Exception:
                pass

# ─── Pipeline Duas Passagens ─────────────────────────────────────────────
async def extrair_com_duas_passagens(pdf_path: Path) -> list[dict]:
    """Passagem 1 (principal) + Passagem 2 (complementar para gaps)."""
    
    # 1. Converte PDF para imagens
    image_paths = pdf_para_imagens(pdf_path, IMAGES_DIR, dpi=200)
    total_pages = len(image_paths)
    logger.info(f"Total de páginas: {total_pages}")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # ─── PASSAGEM 1: Principal ───
    LOTE_SIZE = 4  # 4 páginas = ~12 questões
    todas_questoes = []
    
    for i in range(0, total_pages, LOTE_SIZE):
        lote = image_paths[i:i+LOTE_SIZE]
        inicio = i + 1
        
        logger.info(f"[PASS 1] Lote {i//LOTE_SIZE + 1}/{(total_pages-1)//LOTE_SIZE + 1}: páginas {i+1}-{min(i+LOTE_SIZE, total_pages)}")
        
        questoes_lote = await extrair_lote_principal(client, lote, inicio)
        logger.success(f"  Retornou {len(questoes_lote)} questões")
        todas_questoes.extend(questoes_lote)
    
    # Ordena e dedup
    todas_questoes.sort(key=lambda q: q.get('posicao', 0))
    vistas = set()
    unicas = []
    for q in todas_questoes:
        pos = q.get('posicao')
        if pos and pos not in vistas:
            vistas.add(pos)
            unicas.append(q)
        elif pos:
            logger.warning(f"Duplicata posição {pos} removida")
    
    posicoes_encontradas = {q['posicao'] for q in unicas if q.get('posicao')}
    logger.info(f"[PASS 1] Questões únicas: {len(unicas)} | Posições: {sorted(posicoes_encontradas)}")
    
    # ─── IDENTIFICA GAPS ───
    posicoes_esperadas = set(range(1, 91))  # ENEM tem 90 questões dia 1
    posicoes_faltando = sorted(posicoes_esperadas - posicoes_encontradas)
    
    if posicoes_faltando:
        logger.warning(f"[GAPS] {len(posicoes_faltando)} questões faltando: {posicoes_faltando[:20]}{'...' if len(posicoes_faltando) > 20 else ''}")
        
        # Agrupa posições faltando por página provável
        # Cada página ~3 questões
        paginas_para_reprocessar = set()
        for pos in posicoes_faltando:
            pagina_estimada = max(1, (pos - 1) // 3 + 1)
            if pagina_estimada <= total_pages:
                paginas_para_reprocessar.add(pagina_estimada)
        
        paginas_para_reprocessar = sorted(paginas_para_reprocessar)
        logger.info(f"[PASS 2] Reprocessando páginas: {paginas_para_reprocessar}")
        
        # ─── PASSAGEM 2: Complementar ───
        questoes_complementares = []
        
        # Processa em lotes de 2 páginas (mais focado)
        for i in range(0, len(paginas_para_reprocessar), 2):
            paginas_lote = paginas_para_reprocessar[i:i+2]
            image_lote = [image_paths[p-1] for p in paginas_lote if p <= total_pages]
            
            if not image_lote:
                continue
            
            # Determina quais questões podem estar nessas páginas
            pos_min = min((p-1)*3 + 1 for p in paginas_lote)
            pos_max = min(p*3 for p in paginas_lote)
            questoes_alvo = [p for p in posicoes_faltando if pos_min <= p <= pos_max]
            
            if not questoes_alvo:
                continue
            
            logger.info(f"[PASS 2] Lote páginas {paginas_lote}: buscando questões {questoes_alvo}")
            
            complementares = await extrair_lote_complementar(client, image_lote, questoes_alvo)
            
            # Filtra apenas as que realmente faltam
            for q in complementares:
                pos = q.get('posicao')
                if pos in posicoes_faltando:
                    questoes_complementares.append(q)
                    logger.success(f"  Recuperou Q{pos}")
        
        # Merge: complementares substituem/preenchem gaps
        pos_complementares = {q['posicao'] for q in questoes_complementares if q.get('posicao')}
        unicas = [q for q in unicas if q.get('posicao') not in pos_complementares]
        unicas.extend(questoes_complementares)
        unicas.sort(key=lambda q: q.get('posicao', 0))
        
        logger.success(f"[PASS 2] Recuperadas {len(questoes_complementares)} questões. Total final: {len(unicas)}")
    else:
        logger.success(f"[PASS 1] Sem gaps! Total: {len(unicas)} questões")
    
    return unicas

# ─── Validação ───────────────────────────────────────────────────────────
def validar_extraido(questoes: list[dict]) -> list[QuestaoExtraida]:
    validadas = []
    erros = []
    
    for i, q in enumerate(questoes):
        try:
            validada = QuestaoExtraida(**q)
            
            if validada.posicao != i + 1:
                logger.warning(f"Posição fora de ordem: esperado {i+1}, veio {validada.posicao}")
            
            if not validada.enunciado.strip():
                logger.warning(f"Q{validada.posicao}: enunciado vazio")
            
            if not validada.alternativas.A.strip():
                logger.warning(f"Q{validada.posicao}: alternativa A vazia")
            
            validadas.append(validada)
            
        except Exception as e:
            erros.append(f"Q{i+1} (pos={q.get('posicao', '?')}): {e}")
            logger.error(f"Falha validação Q{i+1}: {e}")
    
    if erros:
        logger.error(f"Total erros validação: {len(erros)}")
        for e in erros[:5]:
            logger.error(f"  - {e}")
    
    logger.success(f"Questões válidas: {len(validadas)}/{len(questoes)}")
    return validadas

# ─── Main ────────────────────────────────────────────────────────────────
async def main():
    logger.add("/home/gumentz/enem-pipeline/logs/extract_2025.log", rotation="10 MB")
    logger.info("=== INÍCIO EXTRAÇÃO 2025 AZUL DIA 1 (DUAS PASSAGENS) ===")
    
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF não encontrado: {PDF_PATH}")
    
    # Extrai com duas passagens
    raw = await extrair_com_duas_passagens(PDF_PATH)
    
    # Salva raw
    raw_file = OUTPUT_DIR / "AZUL_dia1_raw.json"
    raw_file.write_text(json.dumps(raw, ensure_ascii=False, indent=2))
    logger.info(f"Raw salvo: {raw_file}")
    
    # Valida
    validadas = validar_extraido(raw)
    
    # Salva validado
    output = [q.model_dump() for q in validadas]
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    logger.success(f"✅ Extraído e validado: {OUTPUT_FILE} ({len(validadas)} questões)")
    
    # Stats
    com_imagem = sum(1 for q in validadas if q.metadados_visual.contem_imagem)
    logger.info(f"Com imagem: {com_imagem}/{len(validadas)}")
    if validadas:
        logger.info(f"Q1: {validadas[0].enunciado[:80]}...")
        logger.info(f"Q{len(validadas)}: {validadas[-1].enunciado[:80]}...")

if __name__ == "__main__":
    try:
        import fitz
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "pymupdf", "--break-system-packages", "-q"], check=True)
        import fitz
    
    asyncio.run(main())