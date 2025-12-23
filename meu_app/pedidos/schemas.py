"""
Schemas Pydantic para validação de dados do módulo de pedidos.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ItemPedidoCreateSchema(BaseModel):
    """Schema para criação de item de pedido"""
    produto_id: int = Field(..., gt=0, description="ID do produto")
    quantidade: int = Field(..., gt=0, description="Quantidade")
    preco_venda: Decimal = Field(..., gt=0, description="Preço de venda")
    
    @validator('quantidade')
    def validar_quantidade(cls, v):
        """Valida quantidade"""
        if v <= 0:
            raise ValueError('Quantidade deve ser maior que zero')
        return v


class PedidoCreateSchema(BaseModel):
    """Schema para criação de pedido"""
    cliente_id: int = Field(..., gt=0, description="ID do cliente")
    itens: List[ItemPedidoCreateSchema] = Field(..., min_items=1, description="Lista de itens")
    
    @validator('itens')
    def validar_itens(cls, v):
        """Valida lista de itens"""
        if not v or len(v) == 0:
            raise ValueError('Pedido deve ter pelo menos um item')
        return v


class PedidoUpdateSchema(BaseModel):
    """Schema para atualização de pedido"""
    status: Optional[str] = None
    confirmado_comercial: Optional[bool] = None


class PagamentoCreateSchema(BaseModel):
    """Schema para criação de pagamento"""
    pedido_id: int = Field(..., gt=0, description="ID do pedido")
    valor: Decimal = Field(..., gt=0, description="Valor do pagamento")
    metodo_pagamento: str = Field(..., min_length=2, max_length=255, description="Método de pagamento")
    observacoes: Optional[str] = Field(None, max_length=1000, description="Observações")
    
    @validator('valor')
    def validar_valor(cls, v):
        """Valida valor"""
        if v <= 0:
            raise ValueError('Valor deve ser maior que zero')
        return v
    
    @validator('metodo_pagamento')
    def validar_metodo(cls, v):
        """Valida método de pagamento"""
        if not v or not v.strip():
            raise ValueError('Método de pagamento é obrigatório')
        return v.strip()


class ItemPedidoResponseSchema(BaseModel):
    """Schema para resposta de item de pedido"""
    id: int
    pedido_id: int
    produto_id: int
    quantidade: int
    preco_venda: Decimal
    valor_total_venda: Decimal
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class PagamentoResponseSchema(BaseModel):
    """Schema para resposta de pagamento"""
    id: int
    pedido_id: int
    valor: Decimal
    data_pagamento: datetime
    metodo_pagamento: str
    observacoes: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PedidoResponseSchema(BaseModel):
    """Schema para resposta de pedido"""
    id: int
    cliente_id: int
    data: datetime
    status: str
    confirmado_comercial: bool
    confirmado_por: Optional[str] = None
    data_confirmacao: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
