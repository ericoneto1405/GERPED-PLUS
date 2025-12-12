"""
Repository para o módulo financeiro.

Implementa o padrão Repository para acesso a dados financeiros.
"""

from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from ..models import db, Pagamento, OcrQuota, PagamentoAnexo


class PagamentoFinanceiroRepository:
    """
    Repository específico para operações financeiras de pagamentos.
    
    Complementa o PagamentoRepository de pedidos com funcionalidades
    específicas do módulo financeiro.
    """
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_id(self, pagamento_id: int) -> Optional[Pagamento]:
        """Busca pagamento por ID."""
        try:
            return Pagamento.query.get(pagamento_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar pagamento por ID {pagamento_id}: {str(e)}")
            return None
    
    def buscar_por_sha256(self, sha256: str) -> Optional[Pagamento]:
        """Busca pagamento por hash SHA256 do recibo."""
        try:
            try:
                anexo = PagamentoAnexo.query.filter_by(sha256=sha256).first()
            except SQLAlchemyError:
                anexo = None
            if anexo:
                return anexo.pagamento
            return Pagamento.query.filter_by(recibo_sha256=sha256).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar pagamento por SHA256: {str(e)}")
            return None
    
    def listar_todos_com_recibo(self, limit: int = 1000) -> List[Pagamento]:
        """Lista pagamentos que têm recibo anexado."""
        try:
            return Pagamento.query.filter(Pagamento.caminho_recibo.isnot(None))\
                .order_by(Pagamento.data_pagamento.desc())\
                .limit(limit).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pagamentos com recibo: {str(e)}")
            return []
    
    def listar_por_periodo(self, data_inicio: datetime, data_fim: datetime) -> List[Pagamento]:
        """Lista pagamentos em um período."""
        try:
            return Pagamento.query.filter(
                Pagamento.data_pagamento >= data_inicio,
                Pagamento.data_pagamento <= data_fim
            ).order_by(Pagamento.data_pagamento.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pagamentos por período: {str(e)}")
            return []
    
    def listar_pendentes_ocr(self, limit: int = 100) -> List[Pagamento]:
        """Lista pagamentos com recibo mas sem dados de OCR."""
        try:
            return Pagamento.query.filter(
                Pagamento.caminho_recibo.isnot(None),
                Pagamento.ocr_json.is_(None)
            ).order_by(Pagamento.data_pagamento.desc())\
            .limit(limit).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pagamentos pendentes de OCR: {str(e)}")
            return []
    
    def criar(self, pagamento: Pagamento) -> Pagamento:
        """Cria novo pagamento."""
        try:
            self.db.session.add(pagamento)
            self.db.session.commit()
            return pagamento
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar pagamento: {str(e)}")
            raise
    
    def atualizar(self, pagamento: Pagamento) -> Pagamento:
        """Atualiza pagamento existente."""
        try:
            self.db.session.commit()
            return pagamento
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao atualizar pagamento: {str(e)}")
            raise


class OcrQuotaRepository:
    """Repository para controle de quota de OCR."""
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_periodo(self, ano: int, mes: int) -> Optional[OcrQuota]:
        """Busca quota por ano e mês."""
        try:
            return OcrQuota.query.filter_by(ano=ano, mes=mes).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar quota OCR para {mes}/{ano}: {str(e)}")
            return None
    
    def criar(self, quota: OcrQuota) -> OcrQuota:
        """Cria novo registro de quota."""
        try:
            self.db.session.add(quota)
            self.db.session.commit()
            return quota
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar quota OCR: {str(e)}")
            raise
    
    def atualizar(self, quota: OcrQuota) -> OcrQuota:
        """Atualiza quota existente."""
        try:
            self.db.session.commit()
            return quota
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao atualizar quota OCR: {str(e)}")
            raise
    
    def incrementar_contador(self, ano: int, mes: int) -> bool:
        """
        Incrementa contador de OCR do mês.
        
        Returns:
            True se incrementado com sucesso
        """
        try:
            quota = self.buscar_por_periodo(ano, mes)
            if not quota:
                # Criar novo registro se não existir
                quota = OcrQuota(ano=ano, mes=mes, contador=1)
                self.criar(quota)
            else:
                quota.contador += 1
                self.atualizar(quota)
            return True
        except Exception as e:
            print(f"Erro ao incrementar contador OCR: {str(e)}")
            return False
    
    def obter_contador_mensal(self, ano: int, mes: int) -> int:
        """
        Obtém contador atual do mês.
        
        Returns:
            Número de chamadas de OCR no mês
        """
        try:
            quota = self.buscar_por_periodo(ano, mes)
            return quota.contador if quota else 0
        except Exception as e:
            print(f"Erro ao obter contador OCR: {str(e)}")
            return 0
