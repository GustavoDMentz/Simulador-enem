#!/usr/bin/env python3
"""
Schemas Pydantic v2 para o pipeline ENEM
Documento unificado: QuestaoEnem + validações
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from enum import Enum
import re

class AreaConhecimento(str, Enum):
    CH = "CH"  # Ciências Humanas
    CN = "CN"  # Ciências da Natureza
    LC = "LC"  # Linguagens e Códigos
    MT = "MT"  # Matemática
    REDACAO = "REDACAO"

class CorProva(str, Enum):
    AZUL = "AZUL"
    AMARELO = "AMARELO"
    BRANCO = "BRANCO"
    ROSA = "ROSA"
    VERDE = "VERDE"
    LARANJA = "LARANJA"
    CINZA = "CINZA"
    LILAS = "LILAS"
    LEITOR_TELA = "LEITOR_TELA"
    BRAILE = "BRAILE"
    VERDE_LIBRAS = "VERDE_LIBRAS"

class Alternativas(BaseModel):
    A: str = Field(min_length=1)
    B: str = Field(min_length=1)
    C: str = Field(min_length=1)
    D: str = Field(min_length=1)
    E: str = Field(min_length=1)
    
    @field_validator('*')
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Alternativa não pode ser vazia")
        return v.strip()

class MetadadosVisual(BaseModel):
    contem_imagem: bool
    descricao_imagem: Optional[str] = None
    caminho_local_imagem: Optional[str] = None

class ParametrosTRI(BaseModel):
    a_discriminacao: float = Field(gt=0, description="Parâmetro de discriminação (a > 0)")
    b_dificuldade: float = Field(description="Parâmetro de dificuldade (b ∈ ℝ)")
    c_chute: float = Field(ge=0, le=1, description="Parâmetro de pseudo-chute (0 ≤ c ≤ 1)")
    
    @field_validator('c_chute')
    @classmethod
    def validar_chute(cls, v: float) -> float:
        if v > 0.35:
            # Alerta: c alto indica distratores confusos
            import warnings
            warnings.warn(f"Parâmetro c={v:.4f} alto (>0.35) — distratores podem confundir")
        return v

class ConteudoQuestao(BaseModel):
    enunciado: str = Field(min_length=1)
    texto_base: str = ""
    alternativas: Alternativas
    metadados_visual: MetadadosVisual
    
    @field_validator('enunciado')
    @classmethod
    def enunciado_nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Enunciado não pode ser vazio")
        return v.strip()

class QuestaoEnem(BaseModel):
    """Documento unificado final para ArangoDB"""
    id_unico_sistema: str = Field(pattern=r"^\d{4}_(AZUL|AMARELO|BRANCO|ROSA|VERDE|LARANJA|CINZA|LILAS|LEITOR_TELA|BRAILE|VERDE_LIBRAS)_D[12]_Q\d{2,3}$")
    co_item: int = Field(gt=0, description="Código único do item no banco INEP")
    ano: int = Field(ge=2017, le=2030)
    dia: Literal[1, 2]
    cor_prova: CorProva
    posicao_prova: int = Field(ge=1, le=180)
    area_conhecimento: AreaConhecimento
    gabarito_oficial: Literal["A", "B", "C", "D", "E"]
    co_habilidade: int = Field(ge=0)
    in_item_aban: Literal[0, 1] = 0
    conteudo: ConteudoQuestao
    parametros_tri: ParametrosTRI
    
    @field_validator('id_unico_sistema')
    @classmethod
    def validar_id(cls, v: str) -> str:
        # Valida consistência interna
        partes = v.split('_')
        if len(partes) != 4:
            raise ValueError("ID deve ter formato ANO_COR_DIA_QNN")
        return v
    
    @field_validator('gabarito_oficial')
    @classmethod
    def validar_gabarito(cls, v: str) -> str:
        if v not in {'A', 'B', 'C', 'D', 'E'}:
            raise ValueError("Gabarito deve ser A, B, C, D ou E")
        return v
    
    def to_arango_doc(self) -> dict:
        """Converte para documento ArangoDB (vertex collection 'Questoes')"""
        doc = self.model_dump(mode='json')
        doc['_key'] = self.id_unico_sistema
        return doc

# Validação rápida de consistência LLM ↔ TRI
def validar_consistencia(questao: QuestaoEnem, df_tri_row: dict) -> list[str]:
    """Retorna lista de warnings (não erros) de inconsistências."""
    warnings = []
    
    # Gabarito confere?
    if questao.gabarito_oficial != df_tri_row.get('TX_GABARITO'):
        warnings.append(f"Gabarito divergente: LLM={questao.gabarito_oficial} vs TRI={df_tri_row.get('TX_GABARITO')}")
    
    # CO_ITEM confere?
    if questao.co_item != df_tri_row.get('CO_ITEM'):
        warnings.append(f"CO_ITEM divergente: LLM={questao.co_item} vs TRI={df_tri_row.get('CO_ITEM')}")
    
    # Área confere?
    area_tri = df_tri_row.get('SG_AREA', '').upper()
    if questao.area_conhecimento.value != area_tri:
        warnings.append(f"Área divergente: LLM={questao.area_conhecimento.value} vs TRI={area_tri}")
    
    return warnings