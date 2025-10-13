# run.py
from dotenv import load_dotenv
import os
import sys
import socket

# Carrega as variáveis de ambiente do arquivo .env.dev
dotenv_path = os.path.join(os.path.dirname(__file__), '.env.dev')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)

# FIX: Remover DATABASE_URL do sistema em desenvolvimento (forçar SQLite)
# A variável DATABASE_URL do sistema pode ter valores de exemplo que quebram a app
if os.getenv('FLASK_ENV') != 'production':
    os.environ.pop('DATABASE_URL', None)

def check_port_available(port):
    """Verifica se a porta está disponível"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def get_pid_using_port(port):
    """Obtém o PID do processo usando a porta"""
    try:
        import subprocess
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')
        return []
    except Exception:
        return []

from config import DevelopmentConfig
from meu_app import create_app

app = create_app(DevelopmentConfig)

if __name__ == "__main__":
    PORT = 5004
    HOST = "127.0.0.1"
    
    # Verifica se a porta está disponível (apenas no processo principal)
    # O processo filho do reloader não precisa fazer essa verificação
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    
    if not is_reloader_process and not check_port_available(PORT):
        print(f"\n❌ ERRO: Porta {PORT} já está em uso!\n")
        
        pids = get_pid_using_port(PORT)
        if pids:
            print(f"Processo(s) usando a porta {PORT}:")
            for pid in pids:
                print(f"  - PID: {pid}")
        
        print(f"\n💡 Soluções:")
        print(f"  1. Use o gerenciador de servidor:")
        print(f"     make server-stop    # Para o servidor")
        print(f"     make server-start   # Inicia o servidor")
        print(f"     make server-status  # Verifica status")
        print(f"\n  2. Ou encerre manualmente:")
        if pids:
            print(f"     kill -9 {' '.join(pids)}")
        else:
            print(f"     lsof -ti:{PORT} | xargs kill -9")
        print()
        sys.exit(1)
    
    # Salva PID em arquivo (apenas no processo principal)
    if not is_reloader_process:
        pid_file = '.flask.pid'
        try:
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            print(f"⚠️  Aviso: Não foi possível salvar PID: {e}")
        
        print(f"\n🚀 Iniciando servidor Flask...")
        print(f"   Host: {HOST}")
        print(f"   Porta: {PORT}")
        print(f"   URL: http://{HOST}:{PORT}")
        print(f"   PID: {os.getpid()}\n")
    
    # Evitar problemas com multiprocessing/semaphore em macOS
    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)
    
    try:
        app.run(
            host=HOST, 
            port=PORT, 
            debug=True,
            use_reloader=True,
            threaded=True
        )
    finally:
        # Remove PID file ao encerrar
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
            except Exception:
                pass
