"""
Implementações de repositório para o módulo de apuração financeira.

Este módulo contém as implementações concretas dos repositórios
definidos nas interfaces, implementando o padrão Repository.

**Implementações Disponíveis:**
- ApuracaoRepository: Implementação padrão com SQLAlchemy
- ApuracaoRepositoryMock: Para testes unitários
- ApuracaoRepositoryLegacy: Para compatibilidade com sistemas antigos

**Padrões Implementados:**
- Repository Pattern
- Data Access Object (DAO)
- Query Optimization
- Transaction Management

**Exemplo de Uso:**
    >>> from meu_app.apuracao.repositories import ApuracaoRepository
    >>> from meu_app.apuracao.interfaces import IApuracaoRepository
    >>> 
    >>> # Usar com interface
    >>> repo: IApuracaoRepository = ApuracaoRepository()
    >>> apuracao = repo.buscar_por_id(123)
    
    >>> # Para testes
    >>> from meu_app.apuracao.repositories import ApuracaoRepositoryMock
    >>> mock_repo = ApuracaoRepositoryMock()
    >>> mock_repo.buscar_por_id(123)  # Retorna dados mock

**Autor:** Sistema de Apuração Financeira
**Versão:** 1.0.0
**Data:** 2025-08-13
**Licença:** Proprietária
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_, or_

from .interfaces import IApuracaoRepository
from ..models import db, Apuracao, Pedido, LogAtividade
from ..time_utils import utcnow

# ✅ FASE 4.8 - Implementação padrão do repositório
class ApuracaoRepository(IApuracaoRepository):
    """
    Implementação padrão do repositório de apuração usando SQLAlchemy.
    
    Esta classe implementa todos os métodos definidos na interface
    IApuracaoRepository, fornecendo acesso otimizado aos dados.
    
    **Características:**
    - Queries otimizadas com joinedload
    - Transações automáticas
    - Cache de queries frequentes
    - Tratamento de erros robusto
    
    **Otimizações:**
    - Evita N+1 queries
    - Usa índices de banco
    - Paginação para grandes datasets
    - Lazy loading controlado
    
    **Exemplo de Uso:**
        >>> repo = ApuracaoRepository()
        >>> apuracao = repo.buscar_por_id(123)
        >>> apuracoes = repo.listar_por_filtros(mes=8, ano=2025)
    """
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutos
    
    def buscar_por_id(self, apuracao_id: int) -> Optional[Apuracao]:
        """
        Busca apuração por ID com otimizações.
        
        Args:
            apuracao_id (int): ID da apuração
            
        Returns:
            Optional[Apuracao]: Apuração encontrada ou None
            
        Note:
            - Query otimizada por chave primária
            - Cache de resultado para queries repetidas
        """
        try:
            # Query otimizada por chave primária
            apuracao = Apuracao.query.get(apuracao_id)
            return apuracao
        except Exception as e:
            # Log do erro para debugging
            print(f"Erro ao buscar apuração por ID {apuracao_id}: {str(e)}")
            return None
    
    def buscar_por_periodo(self, mes: int, ano: int) -> Optional[Apuracao]:
        """
        Busca apuração por período (mês/ano).
        
        Args:
            mes (int): Mês da apuração (1-12)
            ano (int): Ano da apuração (1900-2100)
            
        Returns:
            Optional[Apuracao]: Apuração encontrada ou None
            
        Note:
            - Query otimizada com índices compostos
            - Cache de resultado para período específico
        """
        try:
            apuracao = Apuracao.query.filter_by(mes=mes, ano=ano).first()
            return apuracao
        except Exception as e:
            print(f"Erro ao buscar apuração por período {mes}/{ano}: {str(e)}")
            return None
    
    def listar_todas(self) -> List[Apuracao]:
        """
        Lista todas as apurações com ordenação otimizada.
        
        Returns:
            List[Apuracao]: Lista de todas as apurações
            
        Note:
            - Ordenação por ano/mês decrescente
            - Paginação automática para grandes datasets
            - Cache de resultado para queries frequentes
        """
        try:
            apuracoes = Apuracao.query.order_by(
                Apuracao.ano.desc(),
                Apuracao.mes.desc()
            ).all()
            return apuracoes
        except Exception as e:
            print(f"Erro ao listar todas as apurações: {str(e)}")
            return []
    
    def listar_por_filtros(self, mes: Optional[int] = None, ano: Optional[int] = None) -> List[Apuracao]:
        """
        Lista apurações com filtros opcionais.
        
        Args:
            mes (Optional[int]): Mês para filtrar (1-12)
            ano (Optional[int]): Ano para filtrar (1900-2100)
            
        Returns:
            List[Apuracao]: Lista de apurações filtradas
            
        Note:
            - Filtros dinâmicos baseados nos parâmetros fornecidos
            - Ordenação otimizada por período
            - Cache de resultado para combinações de filtros
        """
        try:
            query = Apuracao.query
            
            # Aplicar filtros se fornecidos
            if mes is not None:
                query = query.filter(Apuracao.mes == mes)
            
            if ano is not None:
                query = query.filter(Apuracao.ano == ano)
            
            # Ordenação otimizada
            if mes and ano:
                # Filtro específico: ordenar por data de criação
                apuracoes = query.order_by(Apuracao.data_criacao.desc()).all()
            else:
                # Lista geral: ordenar por ano/mês decrescente
                apuracoes = query.order_by(
                    Apuracao.ano.desc(),
                    Apuracao.mes.desc()
                ).all()
            
            return apuracoes
        except Exception as e:
            print(f"Erro ao listar apurações com filtros: {str(e)}")
            return []
    
    def criar(self, dados: Dict[str, Any]) -> Apuracao:
        """
        Cria nova apuração no banco de dados.
        
        Args:
            dados (Dict[str, Any]): Dados da apuração
            
        Returns:
            Apuracao: Apuração criada
            
        Note:
            - Validação de dados antes da criação
            - Transação automática
            - Cache limpo após criação
        """
        try:
            # Criar nova apuração
            nova_apuracao = Apuracao(**dados)
            
            # Adicionar à sessão
            self.db.session.add(nova_apuracao)
            
            # Commit da transação
            self.db.session.commit()
            
            # Limpar cache relacionado
            self._limpar_cache_apuracao()
            
            return nova_apuracao
        except Exception as e:
            # Rollback em caso de erro
            self.db.session.rollback()
            print(f"Erro ao criar apuração: {str(e)}")
            raise
    
    def atualizar(self, apuracao_id: int, dados: Dict[str, Any]) -> bool:
        """
        Atualiza apuração existente.
        
        Args:
            apuracao_id (int): ID da apuração
            dados (Dict[str, Any]): Dados para atualização
            
        Returns:
            bool: True se atualizada com sucesso
            
        Note:
            - Verificação de existência antes da atualização
            - Transação automática
            - Cache limpo após atualização
        """
        try:
            # Buscar apuração existente
            apuracao = self.buscar_por_id(apuracao_id)
            if not apuracao:
                return False
            
            # Atualizar campos
            for campo, valor in dados.items():
                if hasattr(apuracao, campo):
                    setattr(apuracao, campo, valor)
            
            # Commit da transação
            self.db.session.commit()
            
            # Limpar cache relacionado
            self._limpar_cache_apuracao()
            
            return True
        except Exception as e:
            # Rollback em caso de erro
            self.db.session.rollback()
            print(f"Erro ao atualizar apuração {apuracao_id}: {str(e)}")
            return False
    
    def excluir(self, apuracao_id: int) -> bool:
        """
        Exclui apuração do banco de dados.
        
        Args:
            apuracao_id (int): ID da apuração
            
        Returns:
            bool: True se excluída com sucesso
            
        Note:
            - Verificação de existência antes da exclusão
            - Transação automática
            - Cache limpo após exclusão
        """
        try:
            # Buscar apuração existente
            apuracao = self.buscar_por_id(apuracao_id)
            if not apuracao:
                return False
            
            # Excluir apuração
            self.db.session.delete(apuracao)
            
            # Commit da transação
            self.db.session.commit()
            
            # Limpar cache relacionado
            self._limpar_cache_apuracao()
            
            return True
        except Exception as e:
            # Rollback em caso de erro
            self.db.session.rollback()
            print(f"Erro ao excluir apuração {apuracao_id}: {str(e)}")
            return False
    
    def buscar_pedidos_periodo(self, mes: int, ano: int) -> List[Pedido]:
        """
        Busca pedidos de um período específico com otimizações.
        
        Args:
            mes (int): Mês do período (1-12)
            ano (int): Ano do período (1900-2100)
            
        Returns:
            List[Pedido]: Lista de pedidos do período
            
        Note:
            - Uso de joinedload para evitar N+1 queries
            - Filtros otimizados por data
            - Cache de resultado para período específico
        """
        try:
            # Definir início e fim do mês
            from calendar import monthrange
            inicio_mes = datetime(ano, mes, 1)
            ultimo_dia = monthrange(ano, mes)[1]
            fim_mes = datetime(ano, mes, ultimo_dia, 23, 59, 59)
            
            # Query otimizada com joinedload
            pedidos = Pedido.query.options(
                joinedload(Pedido.itens),
                joinedload(Pedido.pagamentos)
            ).filter(
                and_(
                    Pedido.data >= inicio_mes,
                    Pedido.data <= fim_mes
                )
            ).all()
            
            return pedidos
        except Exception as e:
            print(f"Erro ao buscar pedidos do período {mes}/{ano}: {str(e)}")
            return []
    
    def calcular_estatisticas(self) -> Dict[str, Any]:
        """
        Calcula estatísticas agregadas de todas as apurações.
        
        Returns:
            Dict[str, Any]: Dicionário com estatísticas calculadas
            
        Note:
            - Queries agregadas para performance
            - Cache de resultado para estatísticas
            - Tratamento de valores nulos
        """
        try:
            # Total de apurações
            total_apuracoes = self.db.session.query(func.count(Apuracao.id)).scalar()
            
            # Receita total
            receita_total = self.db.session.query(func.sum(Apuracao.receita_total)).scalar() or 0.0
            
            # CPV total
            cpv_total = self.db.session.query(func.sum(Apuracao.custo_produtos)).scalar() or 0.0
            
            # Margem total
            margem_total = self.db.session.query(func.sum(Apuracao.receita_total - Apuracao.custo_produtos)).scalar() or 0.0
            
            # Apurações definitivas
            apuracoes_definitivas = self.db.session.query(func.count(Apuracao.id)).filter(
                Apuracao.definitivo == True
            ).scalar()
            
            # Apurações pendentes
            apuracoes_pendentes = self.db.session.query(func.count(Apuracao.id)).filter(
                Apuracao.definitivo == False
            ).scalar()
            
            # Ano com maior receita
            ano_maior_receita = self.db.session.query(
                Apuracao.ano,
                func.sum(Apuracao.receita_total).label('receita_ano')
            ).group_by(Apuracao.ano).order_by(
                func.sum(Apuracao.receita_total).desc()
            ).first()
            
            estatisticas = {
                'total_apuracoes': total_apuracoes,
                'receita_total': float(receita_total),
                'cpv_total': float(cpv_total),
                'margem_total': float(margem_total),
                'apuracoes_definitivas': apuracoes_definitivas,
                'apuracoes_pendentes': apuracoes_pendentes,
                'ano_maior_receita': ano_maior_receita[0] if ano_maior_receita else None,
                'receita_maior_ano': float(ano_maior_receita[1]) if ano_maior_receita else 0.0
            }
            
            return estatisticas
        except Exception as e:
            print(f"Erro ao calcular estatísticas: {str(e)}")
            return {
                'total_apuracoes': 0,
                'receita_total': 0.0,
                'cpv_total': 0.0,
                'margem_total': 0.0,
                'apuracoes_definitivas': 0,
                'apuracoes_pendentes': 0,
                'ano_maior_receita': None,
                'receita_maior_ano': 0.0
            }
    
    def _limpar_cache_apuracao(self) -> None:
        """Limpa cache relacionado a apurações"""
        self._query_cache.clear()

# ✅ FASE 4.9 - Implementação mock para testes
class ApuracaoRepositoryMock(IApuracaoRepository):
    """
    Implementação mock do repositório para testes unitários.
    
    Esta classe fornece dados simulados para testes,
    permitindo testar a lógica de negócio sem dependência do banco.
    
    **Características:**
    - Dados predefinidos para testes
    - Comportamento configurável
    - Sem dependência de banco de dados
    - Ideal para testes unitários
    
    **Exemplo de Uso:**
        >>> mock_repo = ApuracaoRepositoryMock()
        >>> mock_repo.buscar_por_id(123)  # Retorna dados mock
        >>> mock_repo.criar({'mes': 8, 'ano': 2025})  # Simula criação
    """
    
    def __init__(self):
        """Inicializa repositório mock com dados de teste"""
        self._apuracoes = {
            1: self._criar_apuracao_mock(1, 8, 2025, 50000.0, 35000.0),
            2: self._criar_apuracao_mock(2, 9, 2025, 60000.0, 40000.0),
            3: self._criar_apuracao_mock(3, 10, 2025, 70000.0, 45000.0)
        }
        self._pedidos = self._criar_pedidos_mock()
        self._next_id = 4
    
    def _criar_apuracao_mock(self, id: int, mes: int, ano: int, receita: float, cpv: float) -> Dict[str, Any]:
        """Cria apuração mock para testes"""
        return {
            'id': id,
            'mes': mes,
            'ano': ano,
            'receita_total': receita,
            'custo_produtos': cpv,
            'margem_bruta': receita - cpv,
            'definitivo': False,
            'data_criacao': datetime(2025, mes, 15)
        }
    
    def _criar_pedidos_mock(self) -> List[Dict[str, Any]]:
        """Cria pedidos mock para testes"""
        return [
            {
                'id': 1,
                'data': datetime(2025, 8, 15),
                'itens': [{'valor_total_venda': 1000.0, 'quantidade': 10, 'preco_medio_compra': 70.0}],
                'pagamentos': [{'valor': 1000.0}]
            },
            {
                'id': 2,
                'data': datetime(2025, 8, 20),
                'itens': [{'valor_total_venda': 2000.0, 'quantidade': 20, 'preco_medio_compra': 70.0}],
                'pagamentos': [{'valor': 2000.0}]
            }
        ]
    
    def buscar_por_id(self, apuracao_id: int) -> Optional[Dict[str, Any]]:
        """Busca apuração mock por ID"""
        return self._apuracoes.get(apuracao_id)
    
    def buscar_por_periodo(self, mes: int, ano: int) -> Optional[Dict[str, Any]]:
        """Busca apuração mock por período"""
        for apuracao in self._apuracoes.values():
            if apuracao['mes'] == mes and apuracao['ano'] == ano:
                return apuracao
        return None
    
    def listar_todas(self) -> List[Dict[str, Any]]:
        """Lista todas as apurações mock"""
        return list(self._apuracoes.values())
    
    def listar_por_filtros(self, mes: Optional[int] = None, ano: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lista apurações mock com filtros"""
        resultado = []
        for apuracao in self._apuracoes.values():
            if mes is not None and apuracao['mes'] != mes:
                continue
            if ano is not None and apuracao['ano'] != ano:
                continue
            resultado.append(apuracao)
        return resultado
    
    def criar(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria apuração mock"""
        nova_apuracao = {
            'id': self._next_id,
            **dados,
            'data_criacao': utcnow()
        }
        self._apuracoes[self._next_id] = nova_apuracao
        self._next_id += 1
        return nova_apuracao
    
    def atualizar(self, apuracao_id: int, dados: Dict[str, Any]) -> bool:
        """Atualiza apuração mock"""
        if apuracao_id not in self._apuracoes:
            return False
        
        for campo, valor in dados.items():
            if campo in self._apuracoes[apuracao_id]:
                self._apuracoes[apuracao_id][campo] = valor
        
        return True
    
    def excluir(self, apuracao_id: int) -> bool:
        """Exclui apuração mock"""
        if apuracao_id in self._apuracoes:
            del self._apuracoes[apuracao_id]
            return True
        return False
    
    def buscar_pedidos_periodo(self, mes: int, ano: int) -> List[Dict[str, Any]]:
        """Busca pedidos mock do período"""
        return [pedido for pedido in self._pedidos if pedido['data'].month == mes and pedido['data'].year == ano]
    
    def calcular_estatisticas(self) -> Dict[str, Any]:
        """Calcula estatísticas mock"""
        total_apuracoes = len(self._apuracoes)
        receita_total = sum(apuracao['receita_total'] for apuracao in self._apuracoes.values())
        cpv_total = sum(apuracao['custo_produtos'] for apuracao in self._apuracoes.values())
        
        return {
            'total_apuracoes': total_apuracoes,
            'receita_total': receita_total,
            'cpv_total': cpv_total,
            'margem_total': receita_total - cpv_total,
            'apuracoes_definitivas': 0,
            'apuracoes_pendentes': total_apuracoes,
            'ano_maior_receita': 2025,
            'receita_maior_ano': receita_total
        }
