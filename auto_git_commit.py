#!/usr/bin/env python3
"""
Sistema de Auto-Commit para Git
Desenvolvido para: github.com/ericoneto1405/sistema-gerped
"""

import os
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

# Configurações
REPO_DIR = Path(__file__).parent.absolute()
CHECK_INTERVAL = 300  # 5 minutos
LOG_FILE = REPO_DIR / '.git-auto-commit.log'
DEFAULT_BRANCH = 'main'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """Executa comando shell"""
    try:
        result = subprocess.run(
            command, shell=True, cwd=cwd or REPO_DIR,
            capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Erro: {e}")
        return -1, "", str(e)

def has_changes():
    """Verifica se há mudanças"""
    returncode, stdout, _ = run_command("git status --porcelain")
    return returncode == 0 and bool(stdout.strip())

def get_changed_files():
    """Retorna arquivos modificados"""
    returncode, stdout, _ = run_command("git status --porcelain")
    if returncode != 0:
        return []
    files = []
    for line in stdout.strip().split('\n'):
        if line:
            parts = line.strip().split(' ', 1)
            if len(parts) == 2:
                files.append(parts[1].strip())
    return files

def create_commit_message():
    """Cria mensagem de commit"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    files = get_changed_files()
    
    if not files:
        return f"Auto-commit: {timestamp}"
    
    file_list = files[:5]
    file_str = "\n- ".join(file_list)
    
    if len(files) > 5:
        file_str += f"\n- ... e mais {len(files) - 5} arquivo(s)"
    
    return f"""Auto-commit: {timestamp}

Arquivos modificados:
- {file_str}
"""

def auto_commit_and_push():
    """Executa auto-commit e push"""
    try:
        if not has_changes():
            logger.debug("Nenhuma mudança")
            return True
        
        logger.info("Mudanças detectadas...")
        
        # Add
        run_command("git add .")
        
        # Commit
        message = create_commit_message()
        safe_message = message.replace('"', '\\"')
        returncode, _, stderr = run_command(f'git commit -m "{safe_message}"')
        
        if returncode != 0:
            logger.error(f"Erro no commit: {stderr}")
            return False
        
        logger.info("Commit realizado")
        
        # Push
        returncode, _, stderr = run_command(f"git push origin {DEFAULT_BRANCH}")
        
        if returncode != 0:
            logger.warning(f"Falha no push: {stderr}")
            return False
        
        logger.info("Push realizado!")
        return True
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False

def main():
    """Função principal"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            auto_commit_and_push()
        elif sys.argv[1] == '--status':
            if has_changes():
                print("⚠️  Mudanças detectadas")
                files = get_changed_files()
                print(f"Arquivos: {len(files)}")
                for f in files[:10]:
                    print(f"  - {f}")
            else:
                print("✅ Nenhuma mudança")
        else:
            print("Uso: python3 auto_git_commit.py [--once|--status]")
    else:
        # Modo contínuo
        logger.info("Auto-commit iniciado")
        logger.info(f"Intervalo: {CHECK_INTERVAL}s")
        
        while True:
            try:
                auto_commit_and_push()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Encerrado")
                break
            except Exception as e:
                logger.error(f"Erro: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
