# run.py
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env.dev
dotenv_path = os.path.join(os.path.dirname(__file__), '.env.dev')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)

# FIX: Remover DATABASE_URL do sistema em desenvolvimento (forçar SQLite)
# A variável DATABASE_URL do sistema pode ter valores de exemplo que quebram a app
if os.getenv('FLASK_ENV') != 'production':
    os.environ.pop('DATABASE_URL', None)

from config import DevelopmentConfig
from meu_app import create_app

app = create_app(DevelopmentConfig)

if __name__ == "__main__":
    # Evitar problemas com multiprocessing/semaphore em macOS
    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)
    
    app.run(
        host="127.0.0.1", 
        port=5004, 
        debug=True,
        use_reloader=True,
        threaded=True
    )
