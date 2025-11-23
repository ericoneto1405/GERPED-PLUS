"""
Schemas Pydantic para validação de dados do módulo coletas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemColetaSchema(BaseModel):
    """Schema para item de coleta"""

    item_id: int = Field(..., gt=0, description="ID do item do pedido")
    quantidade: int = Field(..., description="Quantidade a ser coletada")

    @field_validator("quantidade")
    @classmethod
    def validar_quantidade(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return value


class ColetaRequestSchema(BaseModel):
    """Schema para requisição de coleta"""

    pedido_id: int = Field(..., gt=0, description="ID do pedido")
    responsavel_coleta_id: int = Field(
        ..., gt=0, description="ID do responsável pela coleta"
    )
    nome_retirada: str = Field(
        ..., max_length=100, description="Nome de quem está retirando"
    )
    documento_retirada: str = Field(
        ..., max_length=20, description="Documento de quem está retirando"
    )
    itens_coleta: List[ItemColetaSchema] = Field(
        ..., min_length=1, description="Lista de itens para coleta"
    )
    observacoes: Optional[str] = Field(
        None, max_length=500, description="Observações opcionais"
    )

    @field_validator("nome_retirada", "documento_retirada")
    @classmethod
    def validar_campo_obrigatorio(cls, value: str, info) -> str:
        if not value or not value.strip():
            if info.field_name == "nome_retirada":
                raise ValueError("Nome da retirada é obrigatório")
            raise ValueError("Documento da retirada é obrigatório")
        return value.strip()


class ColetaResult(BaseModel):
    """Schema para resultado de operações de coleta"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sucesso: bool = Field(..., description="Indica se a operação foi bem-sucedida")
    dados: Optional[Any] = Field(None, description="Dados retornados pela operação")
    mensagem: str = Field(..., description="Mensagem descritiva do resultado")


class ColetaResponseSchema(BaseModel):
    """Schema para resposta de coleta processada"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., gt=0, description="ID da coleta")
    pedido_id: int = Field(..., gt=0, description="ID do pedido")
    responsavel_coleta_id: int = Field(..., gt=0, description="ID do responsável")
    nome_retirada: str = Field(..., description="Nome de quem retirou")
    documento_retirada: str = Field(..., description="Documento de quem retirou")
    status: str = Field(..., description="Status da coleta")
    data_coleta: datetime = Field(..., description="Data da coleta")
    observacoes: Optional[str] = Field(None, description="Observações")
