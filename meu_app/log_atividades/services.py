"""
Serviços para o módulo de log de atividades - Versão Completa
============================================================

Contém toda a lógica de negócio para registro e consulta de atividades
com implementação completa e otimizada.

Autor: Sistema de Gestão Empresarial
Data: 2024
"""
from ..models import db, LogAtividade, Usuario
from flask import current_app, session, request
from typing import Dict, List, Tuple, Optional, Any
import json
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_, func
from ..exceptions import DatabaseError, ValidationError, handle_database_error
from .repositories import LogAtividadeRepository


class LogAtividadesService:
    """Serviço para operações relacionadas ao log de atividades"""
    
    def __init__(self):
        """Inicializa o serviço com seu repository"""
        self.repository = LogAtividadeRepository()
    
    def registrar_atividade(self, tipo_atividade: str, titulo: str, descricao: str, 
                          modulo: str, dados_extras: Dict = None, 
                          usuario_id: int = None, ip_address: str = None) -> Tuple[bool, str, Optional[LogAtividade]]:
        """
        Registra uma atividade no log do sistema
        
        Args:
            tipo_atividade: Tipo da atividade (criacao, edicao, exclusao, etc.)
            titulo: Título da atividade
            descricao: Descrição detalhada
            modulo: Módulo onde ocorreu a atividade
            dados_extras: Dados extras em formato de dicionário
            usuario_id: ID do usuário (se None, usa o da sessão)
            ip_address: Endereço IP do usuário
            
        Returns:
            Tuple[bool, str, Optional[LogAtividade]]: (sucesso, mensagem, atividade)
        """
        try:
            # Obter ID do usuário
            if usuario_id is None:
                usuario_id = session.get('usuario_id')
                if not usuario_id:
                    current_app.logger.warning("Tentativa de registrar atividade sem usuário logado")
                    return False, "Usuário não autenticado", None
            
            # Validar dados obrigatórios
            if not tipo_atividade or not titulo or not modulo:
                return False, "Dados obrigatórios faltando", None
            
            # Preparar dados extras
            dados_json = None
            if dados_extras:
                try:
                    # Converter valores não serializáveis
                    dados_convertidos = {}
                    for key, value in dados_extras.items():
                        if isinstance(value, (datetime,)):
                            dados_convertidos[key] = value.isoformat()
                        elif hasattr(value, '__dict__'):
                            dados_convertidos[key] = str(value)
                        else:
                            dados_convertidos[key] = value
                    
                    dados_json = json.dumps(dados_convertidos, ensure_ascii=False)
                except Exception as e:
                    current_app.logger.warning(f"Erro ao serializar dados extras: {str(e)}")
                    dados_json = json.dumps({"erro": "Dados não serializáveis"})
            
            # Obter IP se não foi fornecido
            if ip_address is None and request:
                ip_address = request.remote_addr
            
            # Criar registro de atividade
            atividade = LogAtividade(
                usuario_id=usuario_id,
                tipo_atividade=tipo_atividade,
                titulo=titulo,
                descricao=descricao,
                modulo=modulo,
                dados_extras=dados_json,
                ip_address=ip_address
            )
            
            # Usar repository para criar
            atividade = self.repository.criar(atividade)
            
            current_app.logger.info(f"Atividade registrada: {tipo_atividade} - {titulo}")
            return True, "Atividade registrada com sucesso", atividade
            
        except Exception as e:
            current_app.logger.error(f"Erro ao registrar atividade: {str(e)}")
            return False, f"Erro ao registrar atividade: {str(e)}", None
    
    def listar_atividades(self, filtro_modulo: str = None, data_inicio: str = None, data_fim: str = None, 
                         page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Lista atividades do sistema com paginação otimizada
        
        Args:
            filtro_modulo: Filtro por módulo
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            page: Número da página (começa em 1)
            per_page: Registros por página
            
        Returns:
            Dict com atividades, paginação e estatísticas
        """
        try:
            query = LogAtividade.query
            
            # Aplicar filtros
            if filtro_modulo:
                query = query.filter(LogAtividade.modulo == filtro_modulo)
            
            # Validação e filtro de data de início
            if data_inicio:
                if not LogAtividadesService._validar_formato_data(data_inicio):
                    raise ValidationError(
                        message="Formato de data de início inválido",
                        error_code="INVALID_DATE_FORMAT",
                        details={'field': 'data_inicio', 'expected_format': 'YYYY-MM-DD'}
                    )
                data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
                query = query.filter(LogAtividade.data_hora >= data_inicio_dt)
            
            # Validação e filtro de data de fim
            if data_fim:
                if not LogAtividadesService._validar_formato_data(data_fim):
                    raise ValidationError(
                        message="Formato de data de fim inválido",
                        error_code="INVALID_DATE_FORMAT",
                        details={'field': 'data_fim', 'expected_format': 'YYYY-MM-DD'}
                    )
                data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                query = query.filter(LogAtividade.data_hora <= data_fim_dt)
            
            # Validar datas (início deve ser menor que fim)
            if data_inicio and data_fim:
                inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
                fim = datetime.strptime(data_fim, "%Y-%m-%d")
                if inicio > fim:
                    raise ValidationError(
                        message="Data de início deve ser menor que a data de fim",
                        error_code="INVALID_DATE_RANGE",
                        details={'data_inicio': data_inicio, 'data_fim': data_fim}
                    )
            
            # Contar total de registros
            total_registros = query.count()
            
            # Calcular paginação
            total_paginas = (total_registros + per_page - 1) // per_page
            page = max(1, min(page, total_paginas)) if total_paginas > 0 else 1
            offset = (page - 1) * per_page
            
            # Ordenar por data mais recente e aplicar paginação com eager loading
            atividades = query.options(
                db.joinedload(LogAtividade.usuario)
            ).order_by(LogAtividade.data_hora.desc()).offset(offset).limit(per_page).all()
            
            return {
                'atividades': atividades,
                'page': page,
                'per_page': per_page,
                'total_registros': total_registros,
                'total_paginas': total_paginas,
                'has_prev': page > 1,
                'has_next': page < total_paginas
            }
            
        except ValidationError:
            raise
        except Exception as e:
            db_error = handle_database_error(e, 'listar_atividades')
            current_app.logger.error(f"Erro ao listar atividades: {str(e)}")
            raise db_error
    
    @staticmethod
    def _validar_formato_data(data_str: str) -> bool:
        """
        Valida se a string está no formato YYYY-MM-DD
        
        Args:
            data_str: String da data
            
        Returns:
            bool: True se o formato for válido
        """
        if not data_str:
            return False
        
        try:
            datetime.strptime(data_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def buscar_atividade(atividade_id: int) -> Optional[LogAtividade]:
        """
        Busca uma atividade por ID
        
        Args:
            atividade_id: ID da atividade
            
        Returns:
            Optional[LogAtividade]: Atividade encontrada ou None
        """
        try:
            return LogAtividade.query.options(
                db.joinedload(LogAtividade.usuario)
            ).get(atividade_id)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar atividade: {str(e)}")
            return None
    
    @staticmethod
    def listar_modulos() -> List[str]:
        """
        Lista todos os módulos disponíveis no log
        
        Returns:
            List[str]: Lista de módulos
        """
        try:
            modulos = db.session.query(LogAtividade.modulo).distinct().all()
            return [modulo[0] for modulo in modulos if modulo[0]]
        except Exception as e:
            current_app.logger.error(f"Erro ao listar módulos: {str(e)}")
            return []
    
    @staticmethod
    def limpar_logs_antigos(dias: int = 90) -> Tuple[bool, str, int]:
        """
        Remove logs mais antigos que o número de dias especificado
        
        Args:
            dias: Número de dias para manter
            
        Returns:
            Tuple[bool, str, int]: (sucesso, mensagem, quantidade_removida)
        """
        try:
            if dias < 1:
                return False, "Número de dias deve ser maior que zero", 0
            
            data_limite = datetime.now() - timedelta(days=dias)
            
            # Contar registros que serão removidos
            quantidade = LogAtividade.query.filter(LogAtividade.data_hora < data_limite).count()
            
            if quantidade == 0:
                return True, "Nenhum registro antigo encontrado para remoção", 0
            
            # Remover registros antigos
            LogAtividade.query.filter(LogAtividade.data_hora < data_limite).delete()
            db.session.commit()
            
            current_app.logger.info(f"Logs antigos removidos: {quantidade} registros")
            
            return True, f"{quantidade} registros removidos com sucesso", quantidade
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao limpar logs antigos: {str(e)}")
            return False, f"Erro ao limpar logs: {str(e)}", 0
    
    @staticmethod
    def obter_estatisticas() -> Dict[str, Any]:
        """
        Obtém estatísticas dos logs de atividades
        
        Returns:
            Dict com estatísticas
        """
        try:
            total_atividades = LogAtividade.query.count()
            
            # Atividades por módulo
            modulos_stats = db.session.query(
                LogAtividade.modulo,
                func.count(LogAtividade.id).label('count')
            ).group_by(LogAtividade.modulo).order_by(func.count(LogAtividade.id).desc()).all()
            
            # Atividades dos últimos 7 dias
            data_7_dias = datetime.now() - timedelta(days=7)
            atividades_7_dias = LogAtividade.query.filter(
                LogAtividade.data_hora >= data_7_dias
            ).count()
            
            # Atividades dos últimos 30 dias
            data_30_dias = datetime.now() - timedelta(days=30)
            atividades_30_dias = LogAtividade.query.filter(
                LogAtividade.data_hora >= data_30_dias
            ).count()
            
            # Atividades por tipo
            tipos_stats = db.session.query(
                LogAtividade.tipo_atividade,
                func.count(LogAtividade.id).label('count')
            ).group_by(LogAtividade.tipo_atividade).order_by(func.count(LogAtividade.id).desc()).all()
            
            return {
                'total_atividades': total_atividades,
                'atividades_7_dias': atividades_7_dias,
                'atividades_30_dias': atividades_30_dias,
                'modulos_stats': {modulo: count for modulo, count in modulos_stats},
                'tipos_stats': {tipo: count for tipo, count in tipos_stats}
            }
            
        except Exception as e:
            current_app.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                'total_atividades': 0,
                'atividades_7_dias': 0,
                'atividades_30_dias': 0,
                'modulos_stats': {},
                'tipos_stats': {}
            }
    
    @staticmethod
    def buscar_atividades_por_usuario(usuario_id: int, limit: int = 50) -> List[LogAtividade]:
        """
        Busca atividades de um usuário específico
        
        Args:
            usuario_id: ID do usuário
            limit: Limite de registros
            
        Returns:
            List[LogAtividade]: Lista de atividades
        """
        try:
            return LogAtividade.query.filter(
                LogAtividade.usuario_id == usuario_id
            ).order_by(LogAtividade.data_hora.desc()).limit(limit).all()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar atividades do usuário: {str(e)}")
            return []
    
    @staticmethod
    def buscar_atividades_por_tipo(tipo_atividade: str, limit: int = 50) -> List[LogAtividade]:
        """
        Busca atividades por tipo
        
        Args:
            tipo_atividade: Tipo da atividade
            limit: Limite de registros
            
        Returns:
            List[LogAtividade]: Lista de atividades
        """
        try:
            return LogAtividade.query.filter(
                LogAtividade.tipo_atividade == tipo_atividade
            ).order_by(LogAtividade.data_hora.desc()).limit(limit).all()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar atividades por tipo: {str(e)}")
            return []
    
    @staticmethod
    def exportar_atividades(formato: str = 'json', filtros: Dict = None) -> Tuple[bool, str, Any]:
        """
        Exporta atividades para diferentes formatos
        
        Args:
            formato: Formato de exportação ('json', 'csv')
            filtros: Filtros a serem aplicados
            
        Returns:
            Tuple[bool, str, Any]: (sucesso, mensagem, dados)
        """
        try:
            query = LogAtividade.query.options(db.joinedload(LogAtividade.usuario))
            
            # Aplicar filtros se fornecidos
            if filtros:
                if filtros.get('modulo'):
                    query = query.filter(LogAtividade.modulo == filtros['modulo'])
                if filtros.get('data_inicio'):
                    data_inicio = datetime.strptime(filtros['data_inicio'], "%Y-%m-%d")
                    query = query.filter(LogAtividade.data_hora >= data_inicio)
                if filtros.get('data_fim'):
                    data_fim = datetime.strptime(filtros['data_fim'], "%Y-%m-%d") + timedelta(days=1)
                    query = query.filter(LogAtividade.data_hora < data_fim)
            
            atividades = query.order_by(LogAtividade.data_hora.desc()).all()
            
            if formato == 'json':
                dados = []
                for atividade in atividades:
                    dados.append({
                        'id': atividade.id,
                        'usuario': atividade.usuario.nome if atividade.usuario else 'N/A',
                        'tipo_atividade': atividade.tipo_atividade,
                        'titulo': atividade.titulo,
                        'descricao': atividade.descricao,
                        'modulo': atividade.modulo,
                        'data_atividade': atividade.data_hora.isoformat(),
                        'ip_address': atividade.ip_address,
                        'dados_extras': json.loads(atividade.dados_extras) if atividade.dados_extras else None
                    })
                return True, "Exportação JSON concluída", dados
            
            elif formato == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Cabeçalho
                writer.writerow([
                    'ID', 'Usuário', 'Tipo', 'Título', 'Descrição', 'Módulo', 
                    'Data', 'IP', 'Dados Extras'
                ])
                
                # Dados
                for atividade in atividades:
                    writer.writerow([
                        atividade.id,
                        atividade.usuario.nome if atividade.usuario else 'N/A',
                        atividade.tipo_atividade,
                        atividade.titulo,
                        atividade.descricao,
                        atividade.modulo,
                        atividade.data_hora.strftime('%Y-%m-%d %H:%M:%S'),
                        atividade.ip_address or '',
                        atividade.dados_extras or ''
                    ])
                
                return True, "Exportação CSV concluída", output.getvalue()
            
            else:
                return False, "Formato de exportação não suportado", None
                
        except Exception as e:
            current_app.logger.error(f"Erro ao exportar atividades: {str(e)}")
            return False, f"Erro na exportação: {str(e)}", None
