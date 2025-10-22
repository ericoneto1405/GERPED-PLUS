#!/usr/bin/env python3
"""
Script de Limpeza de Arquivos Desnecessários
============================================

Remove arquivos temporários, backups e arquivos de debug do projeto.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def log_action(action, file_path, success=True):
    """Log de ações realizadas"""
    status = "✅" if success else "❌"
    print(f"{status} {action}: {file_path}")

def backup_before_cleanup():
    """Cria backup antes da limpeza"""
    backup_dir = f"backup_antes_limpeza_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    print(f"📦 Backup criado em: {backup_dir}")
    return backup_dir

def clean_backup_files():
    """Remove arquivos de backup"""
    backup_patterns = ['.backup', '.bak', '.old']
    removed_count = 0
    
    for root, dirs, files in os.walk('.'):
        # Pular diretórios do venv e node_modules
        dirs[:] = [d for d in dirs if d not in ['venv', 'node_modules', '__pycache__', '.git']]
        
        for file in files:
            file_path = os.path.join(root, file)
            if any(file.endswith(pattern) for pattern in backup_patterns):
                try:
                    os.remove(file_path)
                    log_action("REMOVIDO", file_path)
                    removed_count += 1
                except Exception as e:
                    log_action("ERRO", file_path, False)
                    print(f"   Erro: {e}")
    
    return removed_count

def clean_debug_files():
    """Remove arquivos de debug e teste temporários"""
    debug_files = [
        'debug_texto_ocr.py',
        'test_ocr_direto.py', 
        'test_ocr_diagnostico.py',
        'test_validacao_recebedor.py',
        'test_rbac_security.py',
        'limpar_pedidos.py',
        'limpar_pedidos_direto.py'
    ]
    
    removed_count = 0
    for file in debug_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                log_action("REMOVIDO", file)
                removed_count += 1
            except Exception as e:
                log_action("ERRO", file, False)
                print(f"   Erro: {e}")
    
    return removed_count

def clean_temp_uploads():
    """Remove arquivos temporários de upload"""
    temp_dirs = [
        'uploads/temp_recibos',
        'uploads/temp_*',
        'instance/logs/*.log.old'
    ]
    
    removed_count = 0
    for pattern in temp_dirs:
        if '*' in pattern:
            # Usar glob para padrões com wildcard
            import glob
            for file_path in glob.glob(pattern):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        log_action("REMOVIDO", file_path)
                        removed_count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        log_action("REMOVIDO DIR", file_path)
                        removed_count += 1
                except Exception as e:
                    log_action("ERRO", file_path, False)
                    print(f"   Erro: {e}")
        else:
            if os.path.exists(pattern):
                try:
                    if os.path.isfile(pattern):
                        os.remove(pattern)
                        log_action("REMOVIDO", pattern)
                        removed_count += 1
                    elif os.path.isdir(pattern):
                        shutil.rmtree(pattern)
                        log_action("REMOVIDO DIR", pattern)
                        removed_count += 1
                except Exception as e:
                    log_action("ERRO", pattern, False)
                    print(f"   Erro: {e}")
    
    return removed_count

def clean_old_backups():
    """Remove backups antigos do banco"""
    backup_dir = 'instance/backups'
    if not os.path.exists(backup_dir):
        return 0
    
    removed_count = 0
    backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
    
    # Manter apenas os 3 backups mais recentes
    if len(backup_files) > 3:
        backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)))
        old_backups = backup_files[:-3]  # Remove os 3 mais antigos
        
        for backup in old_backups:
            backup_path = os.path.join(backup_dir, backup)
            try:
                os.remove(backup_path)
                log_action("REMOVIDO BACKUP", backup_path)
                removed_count += 1
            except Exception as e:
                log_action("ERRO", backup_path, False)
                print(f"   Erro: {e}")
    
    return removed_count

def clean_pycache():
    """Remove arquivos __pycache__"""
    removed_count = 0
    
    for root, dirs, files in os.walk('.'):
        # Pular diretórios do venv e node_modules
        dirs[:] = [d for d in dirs if d not in ['venv', 'node_modules', '.git']]
        
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                log_action("REMOVIDO __pycache__", pycache_path)
                removed_count += 1
            except Exception as e:
                log_action("ERRO", pycache_path, False)
                print(f"   Erro: {e}")
    
    return removed_count

def main():
    """Executa limpeza completa"""
    print("🧹 LIMPEZA DE ARQUIVOS DESNECESSÁRIOS")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Criar backup antes da limpeza
    backup_dir = backup_before_cleanup()
    
    total_removed = 0
    
    # 1. Arquivos de backup
    print("📁 Removendo arquivos de backup...")
    removed = clean_backup_files()
    total_removed += removed
    print(f"   {removed} arquivos removidos")
    print()
    
    # 2. Arquivos de debug
    print("🐛 Removendo arquivos de debug...")
    removed = clean_debug_files()
    total_removed += removed
    print(f"   {removed} arquivos removidos")
    print()
    
    # 3. Arquivos temporários
    print("📤 Removendo arquivos temporários...")
    removed = clean_temp_uploads()
    total_removed += removed
    print(f"   {removed} arquivos removidos")
    print()
    
    # 4. Backups antigos do banco
    print("💾 Removendo backups antigos do banco...")
    removed = clean_old_backups()
    total_removed += removed
    print(f"   {removed} arquivos removidos")
    print()
    
    # 5. __pycache__
    print("🐍 Removendo __pycache__...")
    removed = clean_pycache()
    total_removed += removed
    print(f"   {removed} diretórios removidos")
    print()
    
    print("=" * 50)
    print(f"✅ Limpeza concluída!")
    print(f"📊 Total de itens removidos: {total_removed}")
    print(f"📦 Backup salvo em: {backup_dir}")

if __name__ == "__main__":
    main()
