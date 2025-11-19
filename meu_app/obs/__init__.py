"""
Módulo de Observabilidade
==========================

Sistema completo de logging estruturado e métricas para observabilidade.

Componentes:
- logging: Logging estruturado JSON com request_id
- metrics: Métricas Prometheus para monitoramento
- middleware: Middleware de logging e rastreamento de requests

Autor: Sistema GERPED - Fase 6
Data: Outubro 2025
"""

from .logging import setup_structured_logging, get_logger
from .metrics import init_metrics, track_request
from .middleware import setup_request_tracking

__all__ = [
    'setup_structured_logging',
    'get_logger',
    'init_metrics',
    'track_request',
    'setup_request_tracking'
]

