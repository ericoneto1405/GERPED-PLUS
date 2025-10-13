"""
Schemas Pydantic para validação de dados do módulo de clientes.

Define os schemas de entrada e saída para operações com clientes,
garantindo validação robusta dos dados.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from typing import Optional
from datetime import datetime
import re


class ClienteCreateSchema(BaseModel):
    """Schema para criação de cliente"""
    nome: str = Field(..., min_length=2, max_length=255, description="Nome do cliente")
    fantasia: Optional[str] = Field(None, max_length=255, description="Nome fantasia")
    telefone: str = Field(..., min_length=8, max_length=20, description="Telefone do cliente")
    endereco: str = Field(..., min_length=5, max_length=255, description="Endereço do cliente")
    cidade: str = Field(..., min_length=2, max_length=100, description="Cidade do cliente")
    cpf_cnpj: Optional[str] = Field(None, max_length=20, description="CPF ou CNPJ do cliente")
    
    @field_validator('nome')
    def validar_nome(cls, v):
        """Valida e sanitiza nome"""
        if not v or not v.strip():
            raise ValueError('Nome é obrigatório')
        return v.strip()
    
    @field_validator('telefone')
    def validar_telefone(cls, v):
        """Valida formato de telefone"""
        if not v or not v.strip():
            raise ValueError('Telefone é obrigatório')
        # Remove caracteres não numéricos
        telefone_limpo = re.sub(r'\D', '', v)
        if len(telefone_limpo) < 8:
            raise ValueError('Telefone deve ter pelo menos 8 dígitos')
        return v.strip()
    
    @field_validator('endereco')
    def validar_endereco(cls, v):
        """Valida endereço"""
        if not v or not v.strip():
            raise ValueError('Endereço é obrigatório')
        return v.strip()
    
    @field_validator('cidade')
    def validar_cidade(cls, v):
        """Valida cidade"""
        if not v or not v.strip():
            raise ValueError('Cidade é obrigatória')
        return v.strip()
    
    @field_validator('cpf_cnpj', mode='before')
    def validar_cpf_cnpj(cls, v):
        """Valida CPF/CNPJ se fornecido"""
        if v:
            # Remove caracteres não numéricos
            doc_limpo = re.sub(r'\D', '', v)
            if doc_limpo and len(doc_limpo) not in [11, 14]:
                raise ValueError('CPF deve ter 11 dígitos ou CNPJ 14 dígitos')
            return v.strip() if v else None
        return None
    
    @field_validator('fantasia', mode='before')
    def validar_fantasia(cls, v):
        """Sanitiza nome fantasia"""
        return v.strip() if v and v.strip() else None


class ClienteUpdateSchema(BaseModel):
    """Schema para atualização de cliente"""
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    fantasia: Optional[str] = Field(None, max_length=255)
    telefone: Optional[str] = Field(None, min_length=8, max_length=20)
    endereco: Optional[str] = Field(None, min_length=5, max_length=255)
    cidade: Optional[str] = Field(None, min_length=2, max_length=100)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    
    @field_validator('nome')
    def validar_nome(cls, v):
        """Valida e sanitiza nome"""
        if v is not None:
            if not v.strip():
                raise ValueError('Nome não pode ser vazio')
            return v.strip()
        return v
    
    @field_validator('telefone')
    def validar_telefone(cls, v):
        """Valida formato de telefone"""
        if v is not None:
            if not v.strip():
                raise ValueError('Telefone não pode ser vazio')
            telefone_limpo = re.sub(r'\D', '', v)
            if len(telefone_limpo) < 8:
                raise ValueError('Telefone deve ter pelo menos 8 dígitos')
            return v.strip()
        return v
    
    @field_validator('endereco')
    def validar_endereco(cls, v):
        """Valida endereço"""
        if v is not None:
            if not v.strip():
                raise ValueError('Endereço não pode ser vazio')
            return v.strip()
        return v
    
    @field_validator('cidade')
    def validar_cidade(cls, v):
        """Valida cidade"""
        if v is not None:
            if not v.strip():
                raise ValueError('Cidade não pode ser vazia')
            return v.strip()
        return v
    
    @field_validator('cpf_cnpj', mode='before')
    def validar_cpf_cnpj(cls, v):
        """Valida CPF/CNPJ se fornecido"""
        if v is not None:
            if not v:
                return None
            doc_limpo = re.sub(r'\D', '', v)
            if doc_limpo and len(doc_limpo) not in [11, 14]:
                raise ValueError('CPF deve ter 11 dígitos ou CNPJ 14 dígitos')
            return v.strip()
        return v
    
    @field_validator('fantasia', mode='before')
    def validar_fantasia(cls, v):
        """Sanitiza nome fantasia"""
        if v is not None:
            valor = v.strip()
            return valor if valor else None
        return v


class ClienteResponseSchema(BaseModel):
    """Schema para resposta de cliente"""
    id: int
    nome: str
    fantasia: Optional[str] = None
    telefone: str
    endereco: str
    cidade: str
    cpf_cnpj: Optional[str] = None
    data_cadastro: datetime
    
    model_config = ConfigDict(from_attributes=True)

    @field_serializer('data_cadastro')
    def serialize_data_cadastro(self, value: datetime) -> str:
        """Serializa datetime para ISO 8601"""
        return value.isoformat()


class ClienteBuscaSchema(BaseModel):
    """Schema para busca de clientes"""
    nome: Optional[str] = Field(None, max_length=255)
    cidade: Optional[str] = Field(None, max_length=100)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)


class ClienteListResponseSchema(BaseModel):
    """Schema para lista de clientes"""
    clientes: list[ClienteResponseSchema]
    total: int
    
    model_config = ConfigDict(from_attributes=True)


class RetiranteCreateSchema(BaseModel):
    """Schema para criação de retirante autorizado"""

    nome: str = Field(..., min_length=3, max_length=120)
    cpf: str = Field(..., min_length=11, max_length=14)
    observacoes: Optional[str] = Field(None, max_length=255)

    @field_validator('nome')
    def validar_nome(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Nome é obrigatório')
        return ' '.join(v.split())

    @field_validator('cpf', mode='before')
    def validar_cpf(cls, v: str) -> str:
        if not v:
            raise ValueError('CPF é obrigatório')
        cpf_limpo = re.sub(r'\D', '', str(v))
        if len(cpf_limpo) != 11:
            raise ValueError('CPF deve conter 11 dígitos')
        return cpf_limpo

    @field_validator('observacoes')
    def validar_obs(cls, v: Optional[str]) -> Optional[str]:
        if v:
            valor = v.strip()
            return valor if valor else None
        return None


class RetiranteStatusSchema(BaseModel):
    """Schema simples para alteração de status de retirante"""

    ativo: bool = Field(...)
