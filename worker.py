#!/usr/bin/env python3
"""
RQ Worker - Processa jobs em background
Fase 7 - Processamento Assíncrono

Uso:
    python worker.py

Ou com múltiplos workers:
    python worker.py & python worker.py & python worker.py
"""

import os
import sys
from redis import Redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar path para importar meu_app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    """
    Inicia o worker RQ para processar jobs
    """
    # Obter URL do Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    print("=" * 70)
    print("🚀 RQ Worker - Sistema GERPED")
    print("=" * 70)
    print(f"Redis: {redis_url}")
    print(f"Filas: ocr")
    print("=" * 70)
    print()
    
    try:
        # Conectar ao Redis
        redis_conn = Redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()
        print("✅ Conectado ao Redis")
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao Redis: {e}")
        print(f"   Verifique se o Redis está rodando: redis-server")
        sys.exit(1)
    
    # Criar worker
    with Connection(redis_conn):
        # Use multiple queues so long-running tasks don't block request threads.
        # 'imports' handles planilha processing (produtos/precos), 'pdf' handles receipts.
        queues = [Queue('ocr'), Queue('pdf'), Queue('imports')]
        worker = Worker(queues)
        
        print("✅ Worker iniciado, aguardando jobs...")
        print("   (Ctrl+C para parar)")
        print()
        
        # Iniciar processamento
        worker.work()


if __name__ == '__main__':
    main()
