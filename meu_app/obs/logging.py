"""
Sistema de Logging Estruturado JSON
====================================

Implementa logging estruturado com JSON para melhor observabilidade e análise.

Features:
- Formato JSON para fácil parsing
- Request ID para correlação de logs
- Contexto automático (user, IP, endpoint)
- Rotação de arquivos
- Múltiplos níveis de log

Uso:
    from meu_app.obs import get_logger
    
    logger = get_logger(__name__)
    logger.info("Pedido criado", extra={
        "pedido_id": 123,
        "valor": 1500.00
    })

Autor: Sistema GERPED
"""

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
from flask import has_request_context, request, g

SENSITIVE_KEYS = {'cpf', 'cnpj', 'documento', 'pix', 'email', 'token'}


def _mask_value(value: str) -> str:
    if not isinstance(value, str):
        return value
    masked = re.sub(r'(\b\d{3})\d{5}(\d{3}\b)', r'\1*****\2', value)
    masked = re.sub(r'(\b\d{2})\d{7}(\d{2}\b)', r'\1*****\2', masked)
    masked = re.sub(r'([\w\.\-]+)@([\w\-]+)', r'***@\2', masked)
    return masked


def _mask_sensitive_data(log_record: dict) -> None:
    for key, value in list(log_record.items()):
        key_lower = str(key).lower()
        if key_lower in SENSITIVE_KEYS:
            log_record[key] = _mask_value(str(value))
    message = log_record.get('message')
    if message:
        log_record['message'] = _mask_value(str(message))


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Formatter JSON customizado que adiciona contexto automático.
    
    Adiciona automaticamente:
    - request_id (se disponível)
    - user_id (se autenticado)
    - ip_address (se em contexto de request)
    - method e url (se em contexto de request)
    """
    
    def add_fields(self, log_record, record, message_dict):
        """Adiciona campos customizados ao log"""
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Adicionar contexto da requisição se disponível
        if has_request_context():
            # Request ID
            if hasattr(g, 'request_id'):
                log_record['request_id'] = g.request_id
            
            # User ID (se autenticado)
            if hasattr(g, 'user_id') and g.user_id:
                log_record['user_id'] = g.user_id
            
            # IP do cliente
            log_record['ip_address'] = request.remote_addr
            
            # Método e URL
            log_record['method'] = request.method
            log_record['url'] = request.url
            log_record['endpoint'] = request.endpoint
        
        # Garantir que level seja string
        if 'levelname' in log_record:
            log_record['level'] = log_record.pop('levelname')

        _mask_sensitive_data(log_record)


def setup_structured_logging(app):
    """
    Configura logging estruturado JSON para a aplicação.
    
    Args:
        app: Instância Flask
        
    Configuração:
        - LOG_DIR: Diretório para arquivos de log
        - LOG_LEVEL: Nível de log (DEBUG, INFO, WARNING, ERROR)
        - LOG_MAX_BYTES: Tamanho máximo do arquivo (default: 10MB)
        - LOG_BACKUP_COUNT: Número de backups (default: 5)
    """
    # Criar diretório de logs
    log_dir = app.config.get('LOG_DIR', 'instance/logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Arquivo de log
    log_file = os.path.join(log_dir, 'app.log')
    
    # Configurar formatter JSON
    json_formatter = CustomJsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={
            'asctime': 'timestamp',
            'levelname': 'level',
            'name': 'logger'
        },
        datefmt='%Y-%m-%dT%H:%M:%S',
        timestamp=True
    )
    
    # Handler para arquivo com rotação
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024),  # 10MB
        backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
    )
    file_handler.setFormatter(json_formatter)
    
    # Definir nível de log
    log_level = getattr(
        logging,
        app.config.get('LOG_LEVEL', 'INFO').upper(),
        logging.INFO
    )
    file_handler.setLevel(log_level)
    
    # Handler para console em desenvolvimento (formato legível)
    if app.debug:
        console_handler = logging.StreamHandler()
        
        # Formato simples para console
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        
        app.logger.addHandler(console_handler)
    
    # Adicionar handler ao logger da aplicação
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)
    
    # Remover handlers padrão do Flask
    app.logger.handlers = [h for h in app.logger.handlers if h in [file_handler, console_handler] if app.debug]
    if not app.debug:
        app.logger.handlers = [file_handler]
    
    app.logger.info(
        'Sistema de logging estruturado inicializado',
        extra={
            'log_file': log_file,
            'log_level': logging.getLevelName(log_level),
            'json_format': True
        }
    )


def get_logger(name):
    """
    Retorna um logger configurado com o nome especificado.
    
    Args:
        name: Nome do logger (geralmente __name__)
        
    Returns:
        Logger configurado
        
    Exemplo:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operação concluída", extra={"duration_ms": 150})
    """
    return logging.getLogger(name)
