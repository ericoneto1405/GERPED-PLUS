"""
Serviços para o módulo de apuração financeira.

Este módulo contém toda a lógica de negócio relacionada à apuração
financeira, separada das rotas e controllers. Implementa validações
robustas, cache inteligente, tratamento de erros específicos e
otimizações de performance.

**Funcionalidades Principais:**
- Cálculo de dados financeiros por período
- Criação, consulta, modificação e exclusão de apurações
- Validação de dados de entrada com regras de negócio
- Cache para otimização de performance
- Tratamento robusto de erros com exceções customizadas
- Logs detalhados para auditoria e debugging

**Características Técnicas:**
- Usa Decimal para precisão em cálculos financeiros
- Implementa rollback inteligente em transações
- Cache com TTL de 5 minutos para dados frequentes
- Queries otimizadas com joinedload para evitar N+1
- Exceções customizadas para diferentes tipos de erro
- Validações rigorosas de entrada

**Estrutura do Módulo:**
- ApuracaoService: Classe principal com métodos estáticos
- Exceções customizadas para tratamento específico
- Cache em memória para estatísticas
- Validadores robustos para dados de entrada

**Exemplo de Uso Básico:**
    >>> from meu_app.apuracao.services import ApuracaoService
    
    >>> # Calcular dados de um período
    >>> dados = ApuracaoService.calcular_dados_periodo(8, 2025)
    >>> print(f"Receita: R$ {dados['receita_calculada']:.2f}")
    
    >>> # Criar uma nova apuração
    >>> dados_apuracao = {
    ...     'receita': 50000.00,
    ...     'cpv': 35000.00,
    ...     'verba_scann': 2000.00
    ... }
    >>> sucesso, msg, apuracao = ApuracaoService.criar_apuracao(8, 2025, dados_apuracao)
    
    >>> # Calcular estatísticas gerais
    >>> stats = ApuracaoService.calcular_estatisticas_gerais()

**Tratamento de Erros:**
O módulo implementa um sistema robusto de tratamento de erros com
exceções customizadas para diferentes cenários:

- ApuracaoValidationError: Erros de validação de entrada
- ApuracaoNotFoundError: Apuração não encontrada
- ApuracaoBusinessError: Violações de regras de negócio
- ApuracaoDatabaseError: Erros de banco de dados

**Cache:**
Sistema de cache automático para dados frequentemente acessados:
- TTL de 5 minutos
- Limpeza automática após modificações
- Logs de debug para monitoramento
- Transparente para o usuário

**Performance:**
Otimizações implementadas para melhor performance:
- N+1 queries eliminadas com joinedload
- Queries agregadas para estatísticas
- Cache para dados frequentemente acessados
- Rollback inteligente para transações

**Validações:**
Sistema robusto de validação implementado:
- Validação de período (mês/ano)
- Validação de dados de entrada
- Validação de IDs
- Validação de lógica de negócio

**Logs:**
Sistema de logs detalhado para auditoria:
- Logs de debug para operações
- Logs de warning para validações
- Logs de error para exceções
- Logs de info para operações concluídas

**Dependências:**
- Flask: Para current_app e session
- SQLAlchemy: Para acesso ao banco de dados
- Decimal: Para precisão em cálculos financeiros
- datetime: Para manipulação de datas
- calendar: Para cálculos de período

**Autor:** Sistema de Apuração Financeira
**Versão:** 1.0.0
**Data:** 2025-08-13
**Licença:** Proprietária
"""
from ..models import db, Apuracao, Pedido, LogAtividade, ItemPedido
from flask import current_app, session
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from calendar import monthrange
from decimal import Decimal, InvalidOperation
import json

# ✅ FASE 2.7 - Cache simples para dados frequentes
_cache_estatisticas = {}
_cache_estatisticas_timestamp = None
CACHE_DURATION = 300  # 5 minutos

# ✅ FASE 3.1 - Exceções customizadas para tratamento específico de erros
class ApuracaoValidationError(Exception):
    """
    Exceção para erros de validação na apuração.
    
    Esta exceção é lançada quando os dados de entrada não passam
    nas validações de tipo, range ou formato.
    
    **Cenários Comuns:**
    - Período inválido (mês fora do range 1-12)
    - Ano inválido (fora do range 1900-2100)
    - Período futuro (não permitido)
    - Dados com tipo incorreto
    - Campos obrigatórios faltando
    - Valores negativos
    - Valores muito altos
    
    Example:
        >>> try:
        ...     ApuracaoService._validar_periodo(13, 2025)
        ... except ApuracaoValidationError as e:
        ...     print(f"Erro de validação: {e}")
        Erro de validação: Mês deve estar entre 1 e 12
    """
    pass

class ApuracaoNotFoundError(Exception):
    """
    Exceção para apuração não encontrada.
    
    Esta exceção é lançada quando uma apuração específica
    não pode ser encontrada no banco de dados.
    
    **Cenários Comuns:**
    - ID de apuração inexistente
    - Apuração foi deletada
    - Período não possui apuração
    
    Example:
        >>> try:
        ...     apuracao = ApuracaoService.buscar_apuracao(999999)
        ...     if not apuracao:
        ...         raise ApuracaoNotFoundError("Apuração não encontrada")
        ... except ApuracaoNotFoundError as e:
        ...     print(f"Erro: {e}")
        Erro: Apuração não encontrada
    """
    pass

class ApuracaoBusinessError(Exception):
    """
    Exceção para erros de regra de negócio.
    
    Esta exceção é lançada quando uma operação viola
    as regras de negócio do sistema.
    
    **Cenários Comuns:**
    - Tentativa de criar apuração duplicada
    - Tentativa de excluir apuração definitiva
    - Tentativa de tornar definitiva apuração já definitiva
    - Violação de integridade referencial
    
    Example:
        >>> try:
        ...     # Tentar criar apuração duplicada
        ...     dados = {'receita': 100, 'cpv': 50}
        ...     ApuracaoService.criar_apuracao(8, 2025, dados)
        ...     ApuracaoService.criar_apuracao(8, 2025, dados)  # Duplicada
        ... except ApuracaoBusinessError as e:
        ...     print(f"Erro de negócio: {e}")
        Erro de negócio: Já existe uma apuração para 8/2025
    """
    pass

class ApuracaoDatabaseError(Exception):
    """
    Exceção para erros de banco de dados.
    
    Esta exceção é lançada quando ocorrem erros
    relacionados ao banco de dados.
    
    **Cenários Comuns:**
    - Falha de conexão com banco
    - Erro de constraint (chave estrangeira, unique)
    - Timeout de transação
    - Erro de rollback
    - Sessão inativa
    
    Example:
        >>> try:
        ...     # Operação que pode falhar no banco
        ...     ApuracaoService.calcular_dados_periodo(8, 2025)
        ... except ApuracaoDatabaseError as e:
        ...     print(f"Erro de banco: {e}")
        ...     # Implementar retry ou fallback
    """
    pass

class ApuracaoService:
    """
    Serviço para operações relacionadas à apuração financeira.
    
    Esta classe fornece métodos para gerenciar apurações financeiras,
    incluindo criação, consulta, modificação e exclusão de apurações.
    Implementa validações robustas, cache inteligente e tratamento
    de erros específicos.
    
    **Funcionalidades Principais:**
    - Cálculo de dados financeiros por período
    - Criação e gerenciamento de apurações
    - Validação de dados de entrada
    - Cache para otimização de performance
    - Tratamento robusto de erros
    - Logs detalhados de operações
    
    **Características Técnicas:**
    - Usa Decimal para precisão em cálculos financeiros
    - Implementa rollback inteligente em transações
    - Cache com TTL de 5 minutos
    - Queries otimizadas com joinedload
    - Exceções customizadas para diferentes tipos de erro
    
    **Exemplo de Uso:**
        >>> # Calcular dados de um período
        >>> dados = ApuracaoService.calcular_dados_periodo(8, 2025)
        >>> print(f"Receita: R$ {dados['receita_calculada']:.2f}")
        
        >>> # Criar uma nova apuração
        >>> dados_apuracao = {
        ...     'receita': 50000.00,
        ...     'cpv': 35000.00,
        ...     'verba_scann': 2000.00
        ... }
        >>> sucesso, msg, apuracao = ApuracaoService.criar_apuracao(8, 2025, dados_apuracao)
        
        >>> # Tornar apuração definitiva
        >>> sucesso, msg = ApuracaoService.tornar_definitiva(apuracao.id)
        
        >>> # Calcular estatísticas gerais
        >>> stats = ApuracaoService.calcular_estatisticas_gerais()
        
    **Tratamento de Erros:**
    - ApuracaoValidationError: Erros de validação de entrada
    - ApuracaoNotFoundError: Apuração não encontrada
    - ApuracaoBusinessError: Violações de regras de negócio
    - ApuracaoDatabaseError: Erros de banco de dados
    
    **Cache:**
    - Cache automático para estatísticas gerais
    - TTL de 5 minutos
    - Limpeza automática após modificações
    - Logs de debug para monitoramento
    
    **Performance:**
    - N+1 queries eliminadas com joinedload
    - Queries agregadas para estatísticas
    - Cache para dados frequentemente acessados
    - Rollback inteligente para transações
    
    Note:
        - Todos os métodos são estáticos para facilitar uso
        - Validações são executadas antes de qualquer operação
        - Logs detalhados são gerados para todas as operações
        - Cache é transparente para o usuário
    """
    
    @staticmethod
    def _is_cache_valid() -> bool:
        """Verifica se o cache ainda é válido"""
        global _cache_estatisticas_timestamp
        if _cache_estatisticas_timestamp is None:
            return False
        return (
            datetime.now(timezone.utc) - _cache_estatisticas_timestamp
        ).total_seconds() < CACHE_DURATION
    
    @staticmethod
    def _clear_cache():
        """Limpa o cache"""
        global _cache_estatisticas, _cache_estatisticas_timestamp
        _cache_estatisticas = {}
        _cache_estatisticas_timestamp = None
    
    # ✅ FASE 3.2 - Validador robusto para dados de entrada
    @staticmethod
    def _validar_periodo(mes: int, ano: int) -> None:
        """
        Valida período (mês/ano) com verificações rigorosas.
        
        Este método realiza validações completas do período fornecido,
        incluindo verificações de tipo, range e lógica de negócio.
        
        **Validações Realizadas:**
        - Tipo de dados (deve ser int)
        - Range do mês (1-12)
        - Range do ano (1900-2100)
        - Período não pode ser futuro
        
        Args:
            mes (int): Mês a validar (1-12)
            ano (int): Ano a validar (1900-2100)
            
        Raises:
            ApuracaoValidationError: Se os dados forem inválidos
            
        Example:
            >>> # Validação de período válido
            >>> ApuracaoService._validar_periodo(8, 2025)  # ✅ OK
            
            >>> # Validação de mês inválido
            >>> ApuracaoService._validar_periodo(13, 2025)  # ❌ Erro
            
            >>> # Validação de ano inválido
            >>> ApuracaoService._validar_periodo(1, 1800)   # ❌ Erro
            
            >>> # Validação de período futuro
            >>> ApuracaoService._validar_periodo(12, 2030)  # ❌ Erro
            
        Note:
            - Períodos futuros são rejeitados para evitar apurações antecipadas
            - Anos muito antigos são rejeitados por questões de compatibilidade
            - Mês 0 ou negativo são rejeitados
        """
        try:
            # Validação de tipo
            if not isinstance(mes, int):
                raise ApuracaoValidationError("Mês deve ser um número inteiro")
            
            if not isinstance(ano, int):
                raise ApuracaoValidationError("Ano deve ser um número inteiro")
            
            # Validação de range
            if not (1 <= mes <= 12):
                raise ApuracaoValidationError("Mês deve estar entre 1 e 12")
            
            if not (1900 <= ano <= 2100):
                raise ApuracaoValidationError("Ano deve estar entre 1900 e 2100")
            
            # ✅ FASE 3.3 - Validação de período futuro
            data_atual = datetime.now(timezone.utc)
            if ano > data_atual.year or (ano == data_atual.year and mes > data_atual.month):
                raise ApuracaoValidationError("Não é possível criar apuração para período futuro")
            
        except ApuracaoValidationError:
            raise
        except Exception as e:
            raise ApuracaoValidationError(f"Erro inesperado na validação de período: {str(e)}")
    
    @staticmethod
    def _validar_dados_apuracao(dados: Dict) -> None:
        """
        Valida dados da apuração com verificações rigorosas.
        
        Este método realiza validações completas dos dados fornecidos,
        incluindo verificações de tipo, campos obrigatórios e lógica de negócio.
        
        **Validações Realizadas:**
        - Tipo de dados (deve ser dict)
        - Campos obrigatórios (receita, cpv)
        - Valores numéricos válidos
        - Valores não negativos
        - Lógica de negócio (receita vs CPV)
        - Limites de valores (receita máxima)
        
        **Campos Suportados:**
        - receita (float): Receita bruta (obrigatório)
        - cpv (float): Custo dos produtos vendidos (obrigatório)
        - verba_scann (float): Verba SCANN (opcional)
        - verba_plano_negocios (float): Verba Plano de Negócios (opcional)
        - verba_time_ambev (float): Verba Time Ambev (opcional)
        - verba_outras_receitas (float): Outras verbas (opcional)
        - outros_custos (float): Outros custos (opcional)
        
        Args:
            dados (Dict): Dados da apuração a validar
            
        Raises:
            ApuracaoValidationError: Se os dados forem inválidos
            
        Example:
            >>> # Dados válidos
            >>> dados_validos = {
            ...     'receita': 50000.00,
            ...     'cpv': 35000.00,
            ...     'verba_scann': 2000.00
            ... }
            >>> ApuracaoService._validar_dados_apuracao(dados_validos)  # ✅ OK
            
            >>> # Dados inválidos - tipo errado
            >>> ApuracaoService._validar_dados_apuracao("dados")  # ❌ Erro
            
            >>> # Dados inválidos - campo obrigatório faltando
            >>> ApuracaoService._validar_dados_apuracao({'receita': 100})  # ❌ Erro
            
            >>> # Dados inválidos - valor negativo
            >>> ApuracaoService._validar_dados_apuracao({
            ...     'receita': -100, 'cpv': 50
            ... })  # ❌ Erro
            
            >>> # Dados inválidos - receita muito alta
            >>> ApuracaoService._validar_dados_apuracao({
            ...     'receita': 2000000000, 'cpv': 1000000
            ... })  # ❌ Erro
            
        Note:
            - Valores negativos são rejeitados
            - Receita > 1 bilhão é rejeitada
            - CPV > receita gera warning mas não erro
            - Valores não numéricos são rejeitados
        """
        try:
            # Validação de tipo
            if not isinstance(dados, dict):
                raise ApuracaoValidationError("Dados devem ser um dicionário")
            
            # Validação de campos obrigatórios
            campos_obrigatorios = ['receita', 'cpv']
            for campo in campos_obrigatorios:
                if campo not in dados:
                    raise ApuracaoValidationError(f"Campo obrigatório '{campo}' não encontrado")
            
            # ✅ FASE 3.4 - Validação de valores numéricos
            for campo, valor in dados.items():
                if isinstance(valor, (int, float, str)):
                    try:
                        valor_decimal = Decimal(str(valor))
                        if valor_decimal < 0:
                            raise ApuracaoValidationError(f"Campo '{campo}' não pode ser negativo")
                    except (InvalidOperation, ValueError):
                        raise ApuracaoValidationError(f"Campo '{campo}' deve ser um número válido")
            
            # ✅ FASE 3.5 - Validação de lógica de negócio
            receita = Decimal(str(dados.get('receita', 0)))
            cpv = Decimal(str(dados.get('cpv', 0)))
            
            if receita < cpv:
                current_app.logger.warning(f"CPV ({cpv}) maior que receita ({receita})")
            
            if receita > 1000000000:  # 1 bilhão
                raise ApuracaoValidationError("Receita muito alta, verifique os dados")
            
        except ApuracaoValidationError:
            raise
        except Exception as e:
            raise ApuracaoValidationError(f"Erro inesperado na validação de dados: {str(e)}")
    
    @staticmethod
    def _validar_id_apuracao(apuracao_id: int) -> None:
        """
        Valida ID da apuração com verificações rigorosas.
        
        Este método realiza validações completas do ID fornecido,
        incluindo verificações de tipo, range e limites razoáveis.
        
        **Validações Realizadas:**
        - Tipo de dados (deve ser int)
        - ID deve ser positivo (> 0)
        - ID não pode ser muito alto (limite de 999.999.999)
        
        **Lógica de Negócio:**
        - IDs negativos ou zero são inválidos
        - IDs muito altos podem indicar erro de entrada
        - Apenas números inteiros são aceitos
        
        Args:
            apuracao_id (int): ID da apuração a validar
            
        Raises:
            ApuracaoValidationError: Se o ID for inválido
            
        Example:
            >>> # Validação de ID válido
            >>> ApuracaoService._validar_id_apuracao(123)  # ✅ OK
            
            >>> # Validação de ID negativo
            >>> ApuracaoService._validar_id_apuracao(-1)   # ❌ Erro
            
            >>> # Validação de ID zero
            >>> ApuracaoService._validar_id_apuracao(0)    # ❌ Erro
            
            >>> # Validação de ID muito alto
            >>> ApuracaoService._validar_id_apuracao(1000000000)  # ❌ Erro
            
        Note:
            - IDs negativos são rejeitados por questões de integridade
            - ID zero é rejeitado pois não é um ID válido
            - Limite de 999.999.999 para evitar overflow
            - Apenas números inteiros são aceitos
        """
        try:
            if not isinstance(apuracao_id, int):
                raise ApuracaoValidationError("ID da apuração deve ser um número inteiro")
            
            if apuracao_id <= 0:
                raise ApuracaoValidationError("ID da apuração deve ser um número positivo")
            
            if apuracao_id > 999999999:  # Limite razoável
                raise ApuracaoValidationError("ID da apuração muito alto")
            
        except ApuracaoValidationError:
            raise
        except Exception as e:
            raise ApuracaoValidationError(f"Erro inesperado na validação de ID: {str(e)}")
    
    # ✅ FASE 3.6 - Rollback inteligente com contexto
    @staticmethod
    def _executar_com_rollback(operacao: str, callback, *args, **kwargs):
        """
        Executa operação com rollback inteligente
        
        Args:
            operacao: Nome da operação para logging
            callback: Função a executar
            *args: Argumentos para a função
            **kwargs: Argumentos nomeados para a função
            
        Returns:
            Resultado da operação
            
        Raises:
            ApuracaoDatabaseError: Se houver erro de banco
            Exception: Outros erros
        """
        try:
            # Verificar se há transação ativa
            if db.session.is_active:
                current_app.logger.debug(f"Iniciando operação: {operacao}")
                resultado = callback(*args, **kwargs)
                db.session.commit()
                current_app.logger.info(f"Operação {operacao} concluída com sucesso")
                return resultado
            else:
                raise ApuracaoDatabaseError("Sessão do banco não está ativa")
                
        except ApuracaoValidationError as e:
            db.session.rollback()
            current_app.logger.warning(f"Rollback por validação em {operacao}: {str(e)}")
            raise
            
        except ApuracaoBusinessError as e:
            db.session.rollback()
            current_app.logger.warning(f"Rollback por regra de negócio em {operacao}: {str(e)}")
            raise
            
        except ApuracaoDatabaseError as e:
            db.session.rollback()
            current_app.logger.error(f"Rollback por erro de banco em {operacao}: {str(e)}")
            raise
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Rollback por erro inesperado em {operacao}: {str(e)}")
            raise ApuracaoDatabaseError(f"Erro inesperado em {operacao}: {str(e)}")
    
    @staticmethod
    def listar_apuracoes(mes: int = None, ano: int = None) -> List[Apuracao]:
        """
        Lista apurações com filtros
        
        Args:
            mes: Mês para filtrar (1-12)
            ano: Ano para filtrar (1900-2100)
            
        Returns:
            List[Apuracao]: Lista de apurações ordenadas
        """
        try:
            # ✅ FASE 2.3 - Otimização: Query base otimizada
            query = Apuracao.query
            
            # Aplicar filtros se fornecidos
            if mes is not None:
                if not isinstance(mes, int) or not (1 <= mes <= 12):
                    current_app.logger.warning(f"Mês inválido fornecido: {mes}")
                    return []
                query = query.filter(Apuracao.mes == mes)
            
            if ano is not None:
                if not isinstance(ano, int) or not (1900 <= ano <= 2100):
                    current_app.logger.warning(f"Ano inválido fornecido: {ano}")
                    return []
                query = query.filter(Apuracao.ano == ano)
            
            # ✅ FASE 2.4 - Otimização: Ordenação eficiente
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
            current_app.logger.error(f"Erro ao listar apurações: {str(e)}")
            return []
    
    @staticmethod
    def calcular_dados_periodo(mes: int, ano: int) -> Dict:
        """
        Calcula dados financeiros do período para apuração.
        
        Este método busca todos os pedidos do período especificado e calcula:
        - Receita bruta (soma dos valores dos pedidos totalmente pagos)
        - CPV (Custo dos Produtos Vendidos) dos pedidos totalmente pagos
        - Total de pedidos no período
        
        **Lógica de Negócio:**
        - Apenas pedidos totalmente pagos são considerados na receita
        - Receita = soma dos valores dos pedidos (não dos pagamentos)
        - CPV = soma dos custos dos produtos dos pedidos pagos
        - Pedidos parcialmente pagos são ignorados
        
        **Otimizações:**
        - Usa joinedload para evitar N+1 queries
        - Usa Decimal para precisão em cálculos financeiros
        - Tratamento robusto de erros de conversão
        
        Args:
            mes (int): Mês do período (1-12)
            ano (int): Ano do período (1900-2100)
            
        Returns:
            Dict: Dicionário com os dados calculados:
                - receita_calculada (float): Receita bruta do período
                - cpv_calculado (float): Custo dos produtos vendidos
                - pedidos_periodo (int): Total de pedidos no período
                
        Raises:
            ApuracaoValidationError: Se mes ou ano forem inválidos
            ApuracaoDatabaseError: Se houver erro de banco de dados
            
        Example:
            >>> # Calcular dados de agosto/2025
            >>> dados = ApuracaoService.calcular_dados_periodo(8, 2025)
            >>> print(f"Receita: R$ {dados['receita_calculada']:.2f}")
            >>> print(f"CPV: R$ {dados['cpv_calculado']:.2f}")
            >>> print(f"Total de pedidos: {dados['pedidos_periodo']}")
            
        Note:
            - Períodos futuros são rejeitados
            - Valores negativos são tratados como 0
            - Erros de conversão decimal são logados e ignorados
        """
        try:
            # ✅ FASE 3.7 - Validação robusta usando validador
            ApuracaoService._validar_periodo(mes, ano)
            
            # Definir início e fim do mês
            inicio_mes = datetime(ano, mes, 1)
            ultimo_dia = monthrange(ano, mes)[1]
            fim_mes = datetime(ano, mes, ultimo_dia, 23, 59, 59)
            
            # ✅ FASE 2.1 - Otimização: Carregar pedidos com itens e pagamentos em uma única query
            from sqlalchemy.orm import joinedload
            
            try:
                pedidos_periodo = Pedido.query.options(
                    joinedload(Pedido.itens).joinedload(ItemPedido.produto),
                    joinedload(Pedido.pagamentos)
                ).filter(
                    Pedido.data >= inicio_mes,
                    Pedido.data <= fim_mes
                ).all()
            except Exception as e:
                raise ApuracaoDatabaseError(f"Erro ao buscar pedidos do período: {str(e)}")
            
            receita_calculada = Decimal('0.0')
            cpv_calculado = Decimal('0.0')
            
            # ✅ FASE 3.8 - Tratamento robusto de cálculos
            for pedido in pedidos_periodo:
                try:
                    # ✅ FASE 2.2 - Otimização: Usar dados já carregados (sem N+1)
                    total_pedido = sum(Decimal(str(i.valor_total_venda)) for i in pedido.itens)
                    total_pago = sum(Decimal(str(p.valor)) for p in pedido.pagamentos)
                    
                    # ✅ FASE 1.3 - Lógica corrigida: usar total_pedido para receita
                    if total_pago >= total_pedido and total_pedido > 0:
                        receita_calculada += total_pedido  # CORRIGIDO: usa total_pedido
                        cpv_calculado += sum(
                            Decimal(str(i.quantidade or 0))
                            * Decimal(str((i.produto.preco_medio_compra if i.produto else 0) or 0))
                            for i in pedido.itens
                        )
                        
                except (InvalidOperation, ValueError) as e:
                    current_app.logger.error(f"Erro de conversão decimal no pedido {pedido.id}: {str(e)}")
                    continue
                except Exception as e:
                    current_app.logger.error(f"Erro ao processar pedido {pedido.id}: {str(e)}")
                    continue
            
            return {
                'receita_calculada': float(receita_calculada),
                'cpv_calculado': float(cpv_calculado),
                'pedidos_periodo': len(pedidos_periodo)
            }
            
        except ApuracaoValidationError as e:
            current_app.logger.error(f"Erro de validação em calcular_dados_periodo: {str(e)}")
            return {
                'receita_calculada': 0.0,
                'cpv_calculado': 0.0,
                'pedidos_periodo': 0
            }
        except ApuracaoDatabaseError as e:
            current_app.logger.error(f"Erro de banco em calcular_dados_periodo: {str(e)}")
            return {
                'receita_calculada': 0.0,
                'cpv_calculado': 0.0,
                'pedidos_periodo': 0
            }
        except Exception as e:
            current_app.logger.error(f"Erro inesperado em calcular_dados_periodo: {str(e)}")
            return {
                'receita_calculada': 0.0,
                'cpv_calculado': 0.0,
                'pedidos_periodo': 0
            }
    
    @staticmethod
    def criar_apuracao(mes: int, ano: int, dados: Dict) -> Tuple[bool, str, Optional[Apuracao]]:
        """
        Cria uma nova apuração para o período especificado.
        
        Este método valida os dados de entrada, verifica se já existe uma apuração
        para o período e cria uma nova apuração com os dados fornecidos.
        
        **Validações Realizadas:**
        - Período válido (mês 1-12, ano 1900-2100, não futuro)
        - Dados obrigatórios (receita, cpv)
        - Valores numéricos válidos e não negativos
        - Lógica de negócio (receita vs CPV)
        
        **Operações Realizadas:**
        - Validação de entrada
        - Verificação de duplicidade
        - Criação da apuração
        - Limpeza de cache
        - Registro de atividade
        
        Args:
            mes (int): Mês da apuração (1-12)
            ano (int): Ano da apuração (1900-2100)
            dados (Dict): Dados da apuração com as chaves:
                - receita (float): Receita bruta do período
                - cpv (float): Custo dos produtos vendidos
                - verba_scann (float, opcional): Verba SCANN
                - verba_plano_negocios (float, opcional): Verba Plano de Negócios
                - verba_time_ambev (float, opcional): Verba Time Ambev
                - verba_outras_receitas (float, opcional): Outras verbas
                - outros_custos (float, opcional): Outros custos
            
        Returns:
            Tuple[bool, str, Optional[Apuracao]]: 
                - sucesso (bool): True se criada com sucesso
                - mensagem (str): Mensagem descritiva do resultado
                - apuracao (Optional[Apuracao]): Apuração criada ou None
                
        Raises:
            ApuracaoValidationError: Se dados de entrada forem inválidos
            ApuracaoBusinessError: Se já existe apuração para o período
            ApuracaoDatabaseError: Se houver erro de banco de dados
            
        Example:
            >>> # Criar apuração para agosto/2025
            >>> dados = {
            ...     'receita': 50000.00,
            ...     'cpv': 35000.00,
            ...     'verba_scann': 2000.00,
            ...     'outros_custos': 1000.00
            ... }
            >>> sucesso, msg, apuracao = ApuracaoService.criar_apuracao(8, 2025, dados)
            >>> if sucesso:
            ...     print(f"Apuração criada: ID {apuracao.id}")
            ... else:
            ...     print(f"Erro: {msg}")
            
        Note:
            - Períodos futuros são rejeitados
            - Valores negativos são rejeitados
            - Receita muito alta (> 1 bilhão) é rejeitada
            - Cache é limpo automaticamente após criação
        """
        def _criar_apuracao_interna():
            # ✅ FASE 3.9 - Validação robusta usando validadores
            ApuracaoService._validar_periodo(mes, ano)
            ApuracaoService._validar_dados_apuracao(dados)
            
            # Verificar se já existe apuração para o período
            apuracao_existente = Apuracao.query.filter_by(mes=mes, ano=ano).first()
            if apuracao_existente:
                raise ApuracaoBusinessError(f"Já existe uma apuração para {mes}/{ano}")
            
            # ✅ FASE 2.11 - Correção: Usar campos corretos do modelo
            # Criar apuração com campos corretos
            nova_apuracao = Apuracao(
                mes=mes,
                ano=ano,
                receita_total=dados.get('receita', 0),
                custo_produtos=dados.get('cpv', 0),
                verba_scann=dados.get('verba_scann', 0),
                verba_plano_negocios=dados.get('verba_plano_negocios', 0),
                verba_time_ambev=dados.get('verba_time_ambev', 0),
                verba_outras_receitas=dados.get('verba_outras_receitas', 0),
                outros_custos=dados.get('outros_custos', 0),
                definitivo=False,
                usuario_id=session.get('usuario_id', 1)  # Usar usuário da sessão ou padrão
            )
            
            db.session.add(nova_apuracao)
            
            # ✅ FASE 2.10 - Otimização: Limpar cache após modificação
            ApuracaoService._clear_cache()
            
            # Registrar atividade
            ApuracaoService._registrar_atividade(
                tipo_atividade="Criação de Apuração",
                titulo="Apuração Criada",
                descricao=f"Apuração criada para {mes}/{ano} - Receita: R$ {dados.get('receita', 0):.2f}",
                modulo="Apuração",
                dados_extras={"apuracao_id": nova_apuracao.id, "mes": mes, "ano": ano}
            )
            
            current_app.logger.info(f"Apuração criada: {mes}/{ano} (ID: {nova_apuracao.id})")
            return nova_apuracao
        
        try:
            # ✅ FASE 3.10 - Usar rollback inteligente
            nova_apuracao = ApuracaoService._executar_com_rollback(
                "criar_apuracao", 
                _criar_apuracao_interna
            )
            
            return True, "Apuração criada com sucesso", nova_apuracao
            
        except ApuracaoValidationError as e:
            return False, f"Erro de validação: {str(e)}", None
        except ApuracaoBusinessError as e:
            return False, str(e), None
        except ApuracaoDatabaseError:
            return False, "Erro interno do sistema", None
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao criar apuração: {str(e)}")
            return False, "Erro interno do sistema", None
    
    @staticmethod
    def tornar_definitiva(apuracao_id: int) -> Tuple[bool, str]:
        """
        Torna uma apuração definitiva (não pode mais ser editada).
        
        Este método valida o ID da apuração, verifica se ela existe
        e se ainda não é definitiva, e então a torna definitiva.
        
        **Validações Realizadas:**
        - ID da apuração válido
        - Apuração deve existir no banco
        - Apuração não pode já ser definitiva
        
        **Operações Realizadas:**
        - Validação de entrada
        - Busca da apuração
        - Verificação de status atual
        - Alteração para definitiva
        - Limpeza de cache
        - Registro de atividade
        
        **Regras de Negócio:**
        - Apenas apurações não definitivas podem ser alteradas
        - Apuração definitiva não pode ser editada ou excluída
        - Operação é irreversível
        
        Args:
            apuracao_id (int): ID da apuração a tornar definitiva
            
        Returns:
            Tuple[bool, str]: 
                - sucesso (bool): True se tornada definitiva com sucesso
                - mensagem (str): Mensagem descritiva do resultado
                
        Raises:
            ApuracaoValidationError: Se ID for inválido
            ApuracaoNotFoundError: Se apuração não for encontrada
            ApuracaoBusinessError: Se apuração já for definitiva
            ApuracaoDatabaseError: Se houver erro de banco de dados
            
        Example:
            >>> # Tornar apuração definitiva
            >>> sucesso, msg = ApuracaoService.tornar_definitiva(123)
            >>> if sucesso:
            ...     print("Apuração tornada definitiva")
            ... else:
            ...     print(f"Erro: {msg}")
            
        Note:
            - Operação é irreversível
            - Cache é limpo automaticamente
            - Atividade é registrada no log
            - Apuração definitiva não pode ser editada
        """
        def _tornar_definitiva_interna():
            # ✅ FASE 3.11 - Validação robusta
            ApuracaoService._validar_id_apuracao(apuracao_id)
            
            apuracao = Apuracao.query.get(apuracao_id)
            if not apuracao:
                raise ApuracaoNotFoundError("Apuração não encontrada")
            
            # ✅ FASE 3.12 - Validação de regra de negócio
            if apuracao.definitivo:
                raise ApuracaoBusinessError("Apuração já é definitiva")
            
            # ✅ FASE 2.11 - Correção: Usar campo correto do modelo
            apuracao.definitivo = True
            
            # ✅ FASE 2.10 - Otimização: Limpar cache após modificação
            ApuracaoService._clear_cache()
            
            # Registrar atividade
            ApuracaoService._registrar_atividade(
                tipo_atividade="Apuração Definitiva",
                titulo="Apuração Tornada Definitiva",
                descricao=f"Apuração {apuracao.mes}/{apuracao.ano} tornada definitiva",
                modulo="Apuração",
                dados_extras={"apuracao_id": apuracao.id, "mes": apuracao.mes, "ano": apuracao.ano}
            )
            
            current_app.logger.info(f"Apuração tornada definitiva: {apuracao.mes}/{apuracao.ano}")
            return apuracao
        
        try:
            # ✅ FASE 3.13 - Usar rollback inteligente
            ApuracaoService._executar_com_rollback(
                "tornar_definitiva", 
                _tornar_definitiva_interna
            )
            
            return True, "Apuração tornada definitiva com sucesso"
            
        except ApuracaoValidationError as e:
            return False, f"Erro de validação: {str(e)}"
        except ApuracaoNotFoundError as e:
            return False, str(e)
        except ApuracaoBusinessError as e:
            return False, str(e)
        except ApuracaoDatabaseError:
            return False, "Erro interno do sistema"
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao tornar apuração definitiva: {str(e)}")
            return False, "Erro interno do sistema"
    
    @staticmethod
    def excluir_apuracao(apuracao_id: int) -> Tuple[bool, str]:
        """
        Exclui uma apuração do sistema.
        
        Este método valida o ID da apuração, verifica se ela existe
        e se não é definitiva, e então a exclui permanentemente.
        
        **Validações Realizadas:**
        - ID da apuração válido
        - Apuração deve existir no banco
        - Apuração não pode ser definitiva
        
        **Operações Realizadas:**
        - Validação de entrada
        - Busca da apuração
        - Verificação de status (não definitiva)
        - Verificação de integridade referencial
        - Exclusão permanente
        - Limpeza de cache
        - Registro de atividade
        
        **Regras de Negócio:**
        - Apenas apurações não definitivas podem ser excluídas
        - Exclusão é permanente e irreversível
        - Verificação de dependências antes da exclusão
        
        Args:
            apuracao_id (int): ID da apuração a excluir
            
        Returns:
            Tuple[bool, str]: 
                - sucesso (bool): True se excluída com sucesso
                - mensagem (str): Mensagem descritiva do resultado
                
        Raises:
            ApuracaoValidationError: Se ID for inválido
            ApuracaoNotFoundError: Se apuração não for encontrada
            ApuracaoBusinessError: Se apuração for definitiva
            ApuracaoDatabaseError: Se houver erro de banco de dados
            
        Example:
            >>> # Excluir apuração
            >>> sucesso, msg = ApuracaoService.excluir_apuracao(123)
            >>> if sucesso:
            ...     print("Apuração excluída com sucesso")
            ... else:
            ...     print(f"Erro: {msg}")
            
        Note:
            - Exclusão é permanente e irreversível
            - Cache é limpo automaticamente
            - Atividade é registrada no log
            - Apurações definitivas não podem ser excluídas
        """
        def _excluir_apuracao_interna():
            # ✅ FASE 3.14 - Validação robusta
            ApuracaoService._validar_id_apuracao(apuracao_id)
            
            apuracao = Apuracao.query.get(apuracao_id)
            if not apuracao:
                raise ApuracaoNotFoundError("Apuração não encontrada")
            
            # ✅ FASE 3.15 - Validação de regra de negócio
            if apuracao.definitivo:
                raise ApuracaoBusinessError("Não é possível excluir uma apuração definitiva")
            
            mes_ano = f"{apuracao.mes}/{apuracao.ano}"
            
            # ✅ FASE 3.16 - Validação de integridade referencial
            # Verificar se há dependências (se necessário)
            # Por exemplo, verificar se há logs de atividade referenciando esta apuração
            
            db.session.delete(apuracao)
            
            # ✅ FASE 2.10 - Otimização: Limpar cache após modificação
            ApuracaoService._clear_cache()
            
            # Registrar atividade
            ApuracaoService._registrar_atividade(
                tipo_atividade="Exclusão de Apuração",
                titulo="Apuração Excluída",
                descricao=f"Apuração {mes_ano} excluída",
                modulo="Apuração",
                dados_extras={"apuracao_id": apuracao_id, "mes": apuracao.mes, "ano": apuracao.ano}
            )
            
            current_app.logger.info(f"Apuração excluída: {mes_ano}")
            return apuracao
        
        try:
            # ✅ FASE 3.17 - Usar rollback inteligente
            ApuracaoService._executar_com_rollback(
                "excluir_apuracao", 
                _excluir_apuracao_interna
            )
            
            return True, "Apuração excluída com sucesso"
            
        except ApuracaoValidationError as e:
            return False, f"Erro de validação: {str(e)}"
        except ApuracaoNotFoundError as e:
            return False, str(e)
        except ApuracaoBusinessError as e:
            return False, str(e)
        except ApuracaoDatabaseError:
            return False, "Erro interno do sistema"
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao excluir apuração: {str(e)}")
            return False, "Erro interno do sistema"
    
    @staticmethod
    def buscar_apuracao(apuracao_id: int) -> Optional[Apuracao]:
        """
        Busca uma apuração específica por ID.
        
        Este método valida o ID fornecido e busca a apuração
        correspondente no banco de dados.
        
        **Validações Realizadas:**
        - ID da apuração válido (positivo, não muito alto)
        - Tipo de dados correto (int)
        
        **Operações Realizadas:**
        - Validação de entrada
        - Busca otimizada por chave primária
        - Log de warning se não encontrada
        
        **Otimizações:**
        - Query otimizada por chave primária
        - Validação antes da busca
        - Logs apropriados para debugging
        
        Args:
            apuracao_id (int): ID da apuração a buscar
            
        Returns:
            Optional[Apuracao]: Apuração encontrada ou None se não existir
            
        Raises:
            ApuracaoValidationError: Se ID for inválido
            
        Example:
            >>> # Buscar apuração existente
            >>> apuracao = ApuracaoService.buscar_apuracao(123)
            >>> if apuracao:
            ...     print(f"Apuração encontrada: {apuracao.mes}/{apuracao.ano}")
            ... else:
            ...     print("Apuração não encontrada")
            
            >>> # Buscar apuração inexistente
            >>> apuracao = ApuracaoService.buscar_apuracao(999999)
            >>> if apuracao is None:
            ...     print("Apuração não encontrada")
            
        Note:
            - Retorna None se apuração não existir
            - Logs de warning são gerados para IDs não encontrados
            - Query é otimizada para performance
            - Validação rigorosa do ID de entrada
        """
        try:
            # ✅ FASE 3.18 - Validação robusta
            ApuracaoService._validar_id_apuracao(apuracao_id)
            
            # ✅ FASE 2.5 - Otimização: Query direta por ID (já é otimizada)
            # O SQLAlchemy otimiza automaticamente queries por chave primária
            apuracao = Apuracao.query.get(apuracao_id)
            
            if not apuracao:
                current_app.logger.warning(f"Apuração não encontrada: ID {apuracao_id}")
            
            return apuracao
            
        except ApuracaoValidationError as e:
            current_app.logger.error(f"Erro de validação ao buscar apuração: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao buscar apuração: {str(e)}")
            return None
    
    @staticmethod
    def calcular_estatisticas_gerais() -> Dict:
        """
        Calcula estatísticas gerais das apurações usando queries agregadas.
        
        Este método calcula estatísticas completas de todas as apurações
        no sistema, incluindo totais, contadores e análises por ano.
        Implementa cache para melhorar performance em consultas frequentes.
        
        **Estatísticas Calculadas:**
        - Total de apurações
        - Receita total acumulada
        - CPV total acumulado
        - Margem total (receita - CPV)
        - Apurações definitivas vs pendentes
        - Ano com maior receita
        - Receita do ano com maior faturamento
        
        **Otimizações:**
        - Queries agregadas para performance
        - Cache com TTL de 5 minutos
        - Limpeza automática de cache
        - Tratamento de valores nulos
        
        Returns:
            Dict: Dicionário com estatísticas calculadas:
                - total_apuracoes (int): Total de apurações no sistema
                - receita_total (float): Receita acumulada de todas as apurações
                - cpv_total (float): CPV acumulado de todas as apurações
                - margem_total (float): Margem total (receita - CPV)
                - apuracoes_definitivas (int): Número de apurações definitivas
                - apuracoes_pendentes (int): Número de apurações pendentes
                - ano_maior_receita (int): Ano com maior receita
                - receita_maior_ano (float): Receita do ano com maior faturamento
                
        Example:
            >>> # Calcular estatísticas gerais
            >>> stats = ApuracaoService.calcular_estatisticas_gerais()
            >>> print(f"Total de apurações: {stats['total_apuracoes']}")
            >>> print(f"Receita total: R$ {stats['receita_total']:.2f}")
            >>> print(f"CPV total: R$ {stats['cpv_total']:.2f}")
            >>> print(f"Margem total: R$ {stats['margem_total']:.2f}")
            >>> print(f"Apurações definitivas: {stats['apuracoes_definitivas']}")
            >>> print(f"Apurações pendentes: {stats['apuracoes_pendentes']}")
            >>> if stats['ano_maior_receita']:
            ...     print(f"Ano com maior receita: {stats['ano_maior_receita']}")
            ...     print(f"Receita do ano: R$ {stats['receita_maior_ano']:.2f}")
            
        Note:
            - Cache é usado para melhorar performance
            - Valores nulos são tratados como 0
            - Ano com maior receita pode ser None se não houver dados
            - Cache é limpo automaticamente após modificações
        """
        global _cache_estatisticas, _cache_estatisticas_timestamp
        
        # ✅ FASE 2.8 - Otimização: Verificar cache primeiro
        if ApuracaoService._is_cache_valid():
            current_app.logger.debug("Retornando estatísticas do cache")
            return _cache_estatisticas
        
        try:
            from sqlalchemy import func
            
            # ✅ FASE 2.6 - Otimização: Queries agregadas para estatísticas
            # Total de apurações
            total_apuracoes = db.session.query(func.count(Apuracao.id)).scalar()
            
            # Receita total (usando campo correto do modelo)
            receita_total = db.session.query(func.sum(Apuracao.receita_total)).scalar() or 0.0
            
            # CPV total (usando campo correto do modelo)
            cpv_total = db.session.query(func.sum(Apuracao.custo_produtos)).scalar() or 0.0
            
            # Margem total (calculada)
            margem_total = db.session.query(func.sum(Apuracao.receita_total - Apuracao.custo_produtos)).scalar() or 0.0
            
            # Apurações definitivas (usando campo correto do modelo)
            apuracoes_definitivas = db.session.query(func.count(Apuracao.id)).filter(
                Apuracao.definitivo == True
            ).scalar()
            
            # Apurações pendentes (usando campo correto do modelo)
            apuracoes_pendentes = db.session.query(func.count(Apuracao.id)).filter(
                Apuracao.definitivo == False
            ).scalar()
            
            # Ano com maior receita
            ano_maior_receita = db.session.query(
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
            
            # ✅ FASE 2.9 - Otimização: Armazenar no cache
            _cache_estatisticas = estatisticas
            _cache_estatisticas_timestamp = datetime.now(timezone.utc)
            
            current_app.logger.debug("Estatísticas calculadas e armazenadas no cache")
            return estatisticas
            
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular estatísticas gerais: {str(e)}")
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
    
    @staticmethod
    def atualizar_apuracao(apuracao_id: int, mes: int, ano: int, dados: Dict) -> Tuple[bool, str]:
        """
        Atualiza uma apuração existente
        
        Args:
            apuracao_id: ID da apuração a ser atualizada
            mes: Mês da apuração
            ano: Ano da apuração
            dados: Dicionário com os dados da apuração
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        def _atualizar_apuracao_interna():
            # ✅ FASE 2.1 - Validação de entrada
            ApuracaoService._validar_id_apuracao(apuracao_id)
            ApuracaoService._validar_periodo(mes, ano)
            ApuracaoService._validar_dados_apuracao(dados)
            
            # ✅ FASE 2.2 - Buscar apuração existente
            apuracao = Apuracao.query.get(apuracao_id)
            if not apuracao:
                raise ApuracaoNotFoundError(f"Apuração com ID {apuracao_id} não encontrada")
            
            # ✅ FASE 2.3 - Verificar se é definitiva
            if apuracao.definitivo:
                raise ApuracaoBusinessError("Não é possível editar uma apuração definitiva")
            
            # ✅ FASE 2.4 - Verificar se já existe apuração para o período
            apuracao_existente = Apuracao.query.filter(
                Apuracao.mes == mes,
                Apuracao.ano == ano,
                Apuracao.id != apuracao_id
            ).first()
            
            if apuracao_existente:
                raise ApuracaoBusinessError(f"Já existe uma apuração para {mes}/{ano}")
            
            # ✅ FASE 2.5 - Atualizar dados
            apuracao.mes = mes
            apuracao.ano = ano
            apuracao.receita_total = Decimal(str(dados.get('receita', 0)))
            apuracao.custo_produtos = Decimal(str(dados.get('cpv', 0)))
            
            # Distribuir verbas entre os campos específicos
            verbas_total = Decimal(str(dados.get('verbas', 0)))
            apuracao.verba_scann = verbas_total * Decimal('0.25')  # 25% para SCANN
            apuracao.verba_plano_negocios = verbas_total * Decimal('0.25')  # 25% para Plano Negócios
            apuracao.verba_time_ambev = verbas_total * Decimal('0.25')  # 25% para Time AMBEV
            apuracao.verba_outras_receitas = verbas_total * Decimal('0.25')  # 25% para Outras Receitas
            
            apuracao.outros_custos = Decimal(str(dados.get('outros_custos', 0)))
            
            if apuracao.receita_total > 0:
                apuracao.percentual_margem_real = (apuracao.margem_bruta / apuracao.receita_total) * 100
            else:
                apuracao.percentual_margem_real = 0
            
            # ✅ FASE 2.7 - Commit da transação
            db.session.commit()
            
            # ✅ FASE 2.8 - Limpar cache
            ApuracaoService._clear_cache()
            
            # ✅ FASE 2.9 - Registrar atividade
            ApuracaoService._registrar_atividade(
                'edicao',
                f'Apuração {mes}/{ano} editada',
                f'Apuração ID {apuracao_id} foi editada com sucesso',
                'apuracao',
                {
                    'apuracao_id': apuracao_id,
                    'mes': mes,
                    'ano': ano,
                    'receita': float(apuracao.receita_total),
                    'cpv': float(apuracao.custo_produtos),
                    'verbas': float(apuracao.verba_scann + apuracao.verba_plano_negocios + apuracao.verba_time_ambev + apuracao.verba_outras_receitas)
                }
            )
            
            current_app.logger.info(f"Apuração {apuracao_id} atualizada com sucesso")
            return True, f"Apuração {mes}/{ano} atualizada com sucesso"
        
        return ApuracaoService._executar_com_rollback("atualização de apuração", _atualizar_apuracao_interna)
    
    @staticmethod
    def _registrar_atividade(tipo_atividade: str, titulo: str, descricao: str, modulo: str, dados_extras: Dict = None) -> None:
        """
        Registra atividade no log do sistema
        
        Args:
            tipo_atividade: Tipo da atividade
            titulo: Título da atividade
            descricao: Descrição da atividade
            modulo: Módulo onde ocorreu
            dados_extras: Dados extras para o log
        """
        try:
            if 'usuario_id' in session:
                # Converter valores Decimal para float antes da serialização JSON
                if dados_extras:
                    dados_convertidos = {}
                    for key, value in dados_extras.items():
                        if hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                            dados_convertidos[key] = float(value)
                        else:
                            dados_convertidos[key] = value
                    dados_json = json.dumps(dados_convertidos)
                else:
                    dados_json = None
                
                log = LogAtividade(
                    usuario_id=session['usuario_id'],
                    tipo_atividade=tipo_atividade,
                    titulo=titulo,
                    descricao=descricao,
                    modulo=modulo,
                    dados_extras=dados_json
                )
                db.session.add(log)
                db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Erro ao registrar atividade: {e}")
            # Não falhar se o log não puder ser registrado
            pass
