"""
Schemas para o módulo de Necessidade de Compra
"""

from typing import Optional
from pydantic import BaseModel, Field
from decimal import Decimal


class AnaliseCompraSchema(BaseModel):
    """Schema para análise de necessidade de compra"""
    produto_id: int
    produto_nome: str
    estoque_atual: int = 0
    quantidade_pedidos_pendentes: int = 0
    quantidade_necessaria: int = 0
    sugestao_compra: int = 0
    preco_medio_compra: Decimal = Decimal('0.00')
    valor_total_sugerido: Decimal = Decimal('0.00')
    status: str = "normal"  # normal, alerta, critico
    
    class Config:
        from_attributes = True


class ResumoAnaliseSchema(BaseModel):
    """Schema para resumo da análise"""
    total_produtos: int = 0
    produtos_criticos: int = 0
    produtos_alerta: int = 0
    valor_total_necessario: Decimal = Decimal('0.00')
    
    class Config:
        from_attributes = True
