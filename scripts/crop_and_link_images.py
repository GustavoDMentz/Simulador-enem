#!/usr/bin/env python3
"""
Crop and Link Images: localiza as questões com imagens nos PDFs originais,
recorta as figuras correspondentes e vincula o caminho local no ArangoDB.
"""

import os
import re
import sys
import json
import asyncio
import fitz  # pymupdf
import requests
from pathlib import Path
from loguru import logger

BASE_DIR = Path("/home/gumentz/arquivos_hd/Dados ENEM")
PIPELINE_DIR = Path("/home/gumentz/enem-pipeline")
ARANGO_HOST = "http://localhost:8529"
DB_NAME = "enem"

session = requests.Session()
session.auth = ("root", "")

def check_pdf_matches_day(p_str: str, dia: int) -> bool:
    """Valida se o caminho do PDF corresponde ao dia solicitado (tratando cad_02_dia_1 etc.)."""
    p_str = p_str.lower()
    tokens = re.split(r'[-_\s/.]', p_str)
    tokens = [t for t in tokens if t]
    
    for idx, token in enumerate(tokens):
        if token in ["dia", "caderno", "domingo"]:
            target_val = f"0{dia}"
            target_val_short = f"{dia}"
            
            # Verifica adjacente esquerdo (ex: 2-dia)
            if idx > 0 and tokens[idx-1] in [target_val, target_val_short]:
                if token == "dia" and idx > 1 and tokens[idx-2] in ["cad", "caderno"]:
                    continue
                return True
                
            # Verifica adjacente direito (ex: dia-2)
            if idx < len(tokens) - 1 and tokens[idx+1] in [target_val, target_val_short]:
                return True
    return False

def find_pdf_on_disk(year: int, prova: str, cor: str, dia: int) -> Path:
    """Busca dinamicamente o PDF no HD."""
    year_dir = BASE_DIR / f"microdados_enem_{year}"
    if not year_dir.exists():
        year_dir = BASE_DIR
        
    for root, dirs, files in os.walk(str(year_dir)):
        for f in files:
            if f.lower().endswith(".pdf"):
                f_lower = f.lower()
                p_str = os.path.join(root, f).lower()
                
                # Exclusões padrão
                if any(term in f_lower for term in ["gab", "read", "edital", "manual", "matriz", "guia", "leia", "anexo", "procedimentos"]):
                    continue
                if any(term in f_lower for term in ["ampliada", "superampliada", "libras", "braile", "ledor", "leitor_tela"]):
                    continue
                    
                # Cor
                cor_term = cor.lower()
                if cor_term == "amarelo" and "amarela" in f_lower:
                    pass
                elif cor_term not in f_lower:
                    continue
                    
                # Dia (validação via tokenização)
                if not check_pdf_matches_day(p_str, dia):
                    continue
                        
                # Aplicação
                is_p2 = "p2" in p_str or "p_2" in p_str or "/p2/" in p_str or "/dia 02/" in p_str or "/dia_02/" in p_str or "/dia-02/" in p_str
                is_digital = "digital" in p_str
                
                if prova == "P2":
                    if not is_p2:
                        continue
                elif prova == "DIGITAL":
                    if not is_digital:
                        continue
                else: # P1
                    if is_p2 or is_digital:
                        continue
                        
                return Path(root) / f
    return None

def find_question_page(doc, enunciado: str, texto_base: str, pos: int):
    """Busca o enunciado/texto base no PDF e retorna o índice da página e o retângulo do texto."""
    search_terms = []
    # Limpa espaços e novas linhas
    clean_enunciado = " ".join(enunciado.split())
    clean_texto = " ".join(texto_base.split()) if texto_base else ""
    
    if len(clean_enunciado) >= 30:
        search_terms.append(clean_enunciado[:50])
        search_terms.append(clean_enunciado[:30])
    if len(clean_texto) >= 30:
        search_terms.append(clean_texto[:50])
        search_terms.append(clean_texto[:30])
        
    for term in search_terms:
        for idx in range(len(doc)):
            page = doc[idx]
            rects = page.search_for(term)
            if rects:
                return idx, rects[0]
                
    # Fallback: busca pelo cabeçalho da questão (ex: "QUESTÃO 27")
    # Isso funciona mesmo se o corpo do texto estiver corrompido no PDF
    target_q = f"QUESTÃO {pos}"
    for idx in range(len(doc)):
        page = doc[idx]
        rects = page.search_for(target_q)
        if rects:
            return idx, rects[0]
            
    return None, None

def get_closest_image_rect(page, text_rect, q) -> fitz.Rect:
    """Dada uma página e o retângulo do texto, retorna o retângulo da imagem (raster ou vetor) correspondente."""
    # 1. Tenta imagens raster/bitmap primeiro
    image_list = page.get_images()
    if image_list:
        if len(image_list) == 1:
            xref = image_list[0][0]
            rects = page.get_image_rects(xref)
            if rects:
                return rects[0]
        else:
            closest_rect = None
            min_dist = float("inf")
            for img in image_list:
                xref = img[0]
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                rect = rects[0]
                text_center_y = (text_rect.y0 + text_rect.y1) / 2
                img_center_y = (rect.y0 + rect.y1) / 2
                dist = abs(text_center_y - img_center_y)
                if dist < min_dist:
                    min_dist = dist
                    closest_rect = rect
            if closest_rect:
                return closest_rect

    # 2. Se não houver raster, tenta desenhos vetoriais (tabelas, gráficos, figuras geométricas)
    # y_min deve ser abaixo do cabeçalho da questão para evitar pegar a barra azul ou bullet dots
    y_min = text_rect.y1 + 15
    
    # Determina o limite inferior (y_max) com base na alternativa A ou no cabeçalho da próxima questão
    y_max = page.rect.height - 50
    pos = q["posicao_prova"]
    
    # Tenta buscar a alternativa A pelo texto do gabarito/db
    alt_a_text = q["conteudo"]["alternativas"].get("A", "")
    found_alt = False
    if alt_a_text:
        for length in [30, 20, 10]:
            if len(alt_a_text) >= length:
                alt_rects = page.search_for(alt_a_text[:length])
                if alt_rects:
                    y_max = alt_rects[0].y0 - 5
                    found_alt = True
                    break
                    
    # Se não achou a alternativa (ex: se for gráfico/figura), tenta a próxima questão na página
    if not found_alt:
        next_q_rects = page.search_for(f"QUESTÃO {pos + 1}")
        if next_q_rects:
            y_max = next_q_rects[0].y0 - 10
            
    # 3. Determina se a questão é tela cheia (full-width) ou coluna simples
    mid_x = page.rect.width / 2
    is_full_width = False
    
    # Analisa os blocos de texto da página que estão no intervalo vertical da questão
    blocks = page.get_text("blocks")
    for b in blocks:
        r_box = b[:4]
        if text_rect.y0 - 5 <= r_box[1] <= y_max + 5:
            # Se algum bloco de texto ultrapassa a metade da página, ela é tratada como largura inteira
            if r_box[2] > mid_x + 30:
                is_full_width = True
                break
                
    if is_full_width:
        col_x0 = 0
        col_x1 = page.rect.width
    else:
        # Coluna simples: restringe à metade esquerda ou direita
        if text_rect.x0 < mid_x:
            col_x0 = 0
            col_x1 = mid_x
        else:
            col_x0 = mid_x
            col_x1 = page.rect.width
        
    drawings = page.get_drawings()
    valid_rects = []
    for d in drawings:
        r = d["rect"]
        # Descarta linhas de borda da página inteira ou traços gigantes
        if r.width > page.rect.width - 30 or r.height > page.rect.height - 30:
            continue
            
        # Descarta traços minúsculos isolados (ruído)
        if r.width < 5 and r.height < 5:
            continue
            
        # Verifica se o desenho está na coluna correspondente
        in_col = (col_x0 - 15 <= r.x0) and (r.x1 <= col_x1 + 15)
        # Verifica se o desenho está próximo verticalmente (entre y_min e y_max)
        in_y_range = (y_min <= r.y0) and (r.y1 <= y_max)
        
        if in_col and in_y_range:
            valid_rects.append(r)
            
    if valid_rects:
        union_rect = valid_rects[0]
        for r in valid_rects[1:]:
            union_rect = union_rect | r
        # Garante tamanho mínimo razoável para evitar recortar pequenos pontos perdidos
        if union_rect.width > 15 and union_rect.height > 15:
            return union_rect
            
    return None

def process_question(q: dict, force: bool = False) -> bool:
    """Busca o PDF, extrai a imagem da página e atualiza o banco."""
    key = q["_key"]
    ano = q["ano"]
    dia = q["dia"]
    cor = q["cor_prova"]
    pos = q["posicao_prova"]
    enunciado = q["conteudo"]["enunciado"]
    texto_base = q["conteudo"].get("texto_base", "")
    
    # Se já tiver o arquivo recortado localmente, pula
    if not force and q["conteudo"].get("metadados_visual", {}).get("caminho_local_imagem"):
        local_path = Path(q["conteudo"]["metadados_visual"]["caminho_local_imagem"])
        if local_path.exists():
            logger.info(f"  ⏭️  Questão {key} já possui imagem recortada e vinculada.")
            return True
            
    # Busca o PDF tentando as aplicações P1, P2 e DIGITAL sucessivamente
    pdf_path = None
    found_page_idx = None
    text_rect = None
    doc = None
    
    for prova in ["P1", "P2", "DIGITAL"]:
        p_path = find_pdf_on_disk(ano, prova, cor, dia)
        if p_path and p_path.exists():
            try:
                temp_doc = fitz.open(p_path)
                idx, rect = find_question_page(temp_doc, enunciado, texto_base, pos)
                if idx is not None:
                    pdf_path = p_path
                    found_page_idx = idx
                    text_rect = rect
                    doc = temp_doc
                    break
            except Exception as e:
                logger.error(f"Erro ao abrir/ler PDF {p_path}: {e}")
                
    if not pdf_path or found_page_idx is None:
        logger.warning(f"  ❌ Questão {key}: Não foi possível localizar a página no PDF")
        return False
        
    page = doc[found_page_idx]
    img_rect = get_closest_image_rect(page, text_rect, q)
    
    if not img_rect:
        logger.warning(f"  ❌ Questão {key}: Nenhuma imagem encontrada na página {found_page_idx+1} do PDF")
        return False
        
    # Crop image
    try:
        # Define diretório de saída estruturado
        output_dir = PIPELINE_DIR / "data" / "extracted" / str(ano) / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{cor}_dia{dia}_Q{str(pos).zfill(2)}.png"
        
        # Crop e salva com 150 DPI para boa qualidade
        pix = page.get_pixmap(clip=img_rect, dpi=150)
        pix.save(str(output_path))
        
        # Atualiza no ArangoDB via PATCH (mesclando caminho da imagem no metadados_visual)
        patch_doc = {
            "conteudo": {
                "metadados_visual": {
                    "caminho_local_imagem": str(output_path)
                }
            }
        }
        patch_url = f"{ARANGO_HOST}/_db/{DB_NAME}/_api/document/Questoes/{key}"
        res = session.patch(patch_url, json=patch_doc)
        
        if res.status_code in [200, 201, 202]:
            logger.info(f"  ✅ Questão {key} → Cropped e vinculada: {output_path.name}")
            return True
        else:
            logger.error(f"  ❌ Questão {key}: Falha ao atualizar ArangoDB (HTTP {res.status_code}): {res.text}")
            return False
            
    except Exception as e:
        logger.error(f"  ❌ Questão {key}: Erro ao recortar/vincular imagem: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Crop and link physical images.")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing cropped images.")
    parser.add_argument("--key", type=str, help="Process only a specific question key (e.g. 2023_AZUL_D2_Q110).")
    args = parser.parse_args()

    logger.add("/home/gumentz/enem-pipeline/logs/crop_and_link_images.log", rotation="10 MB")
    logger.info("=== RECORTE E VINCULAÇÃO DE IMAGENS FÍSICAS ===")
    
    # Busca as questões correspondentes no banco de dados
    if args.key:
        query = {
            "query": "FOR q IN Questoes FILTER q._key == @key RETURN q",
            "bindVars": {"key": args.key}
        }
    else:
        query = {
            "query": "FOR q IN Questoes FILTER q.conteudo.metadados_visual.contem_imagem == true RETURN q"
        }
        
    try:
        r = session.post(f"{ARANGO_HOST}/_db/{DB_NAME}/_api/cursor", json=query)
        if r.status_code != 201:
            logger.error(f"Falha ao buscar questões do ArangoDB (HTTP {r.status_code}): {r.text}")
            sys.exit(1)
        questoes = r.json().get("result", [])
    except Exception as e:
        logger.error(f"Erro de conexão com ArangoDB: {e}")
        sys.exit(1)
        
    total = len(questoes)
    logger.info(f"Encontradas {total} questões para processar no banco de dados.")
    
    sucessos = 0
    for idx, q in enumerate(questoes, 1):
        logger.info(f"[{idx}/{total}] Processando {q['_key']}...")
        if process_question(q, force=args.force):
            sucessos += 1
            
    logger.success(f"=== Concluído! {sucessos}/{total} imagens processadas com sucesso ===")

if __name__ == "__main__":
    main()
