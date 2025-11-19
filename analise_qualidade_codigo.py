#!/usr/bin/env python3
"""
Análise de Qualidade de Código - Sistema GERPED
===========================================

Script para identificar problemas de qualidade de código:
- Código duplicado
- Tratamento de exceções inadequado
- Variáveis globais
- Logging inadequado
- Docstrings desatualizadas
"""

import os
import re
import ast
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class CodeQualityAnalyzer:
    def __init__(self):
        self.issues = defaultdict(list)
        self.duplicated_code = []
        self.exceptions_issues = []
        self.global_vars = []
        self.logging_issues = []
        self.docstring_issues = []
        
    def analyze_file(self, file_path):
        """Analisa um arquivo Python"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Análises
            self._check_bare_except(tree, file_path)
            self._check_global_vars(tree, file_path)
            self._check_logging(tree, file_path, content)
            self._check_docstrings(tree, file_path)
            self._check_duplicated_imports(content, file_path)
            
        except Exception as e:
            self.issues['parse_errors'].append(f"{file_path}: {str(e)}")
    
    def _check_bare_except(self, tree, file_path):
        """Verifica bare except: statements"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                self.exceptions_issues.append({
                    'file': file_path,
                    'line': node.lineno,
                    'issue': 'Bare except: statement',
                    'severity': 'HIGH'
                })
    
    def _check_global_vars(self, tree, file_path):
        """Verifica uso de variáveis globais"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    self.global_vars.append({
                        'file': file_path,
                        'line': node.lineno,
                        'variable': name,
                        'severity': 'MEDIUM'
                    })
    
    def _check_logging(self, tree, file_path, content):
        """Verifica logging adequado"""
        # Verificar se há logging em operações críticas
        critical_operations = [
            'db.session.commit',
            'db.session.rollback',
            'session.clear',
            'os.remove',
            'shutil.rmtree'
        ]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr'):
                    operation = f"{node.func.value.id}.{node.func.attr}" if hasattr(node.func, 'value') else node.func.attr
                    if operation in critical_operations:
                        # Verificar se há logging antes/after
                        if not self._has_logging_nearby(content, node.lineno):
                            self.logging_issues.append({
                                'file': file_path,
                                'line': node.lineno,
                                'operation': operation,
                                'severity': 'MEDIUM'
                            })
    
    def _has_logging_nearby(self, content, line_num):
        """Verifica se há logging próximo à linha"""
        lines = content.split('\n')
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 5)
        
        for i in range(start, end):
            if 'logger' in lines[i] or 'log' in lines[i]:
                return True
        return False
    
    def _check_docstrings(self, tree, file_path):
        """Verifica docstrings"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    self.docstring_issues.append({
                        'file': file_path,
                        'line': node.lineno,
                        'name': node.name,
                        'type': type(node).__name__,
                        'severity': 'LOW'
                    })
    
    def _check_duplicated_imports(self, content, file_path):
        """Verifica imports duplicados"""
        import_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append((i, line.strip()))
        
        # Verificar duplicatas
        seen_imports = set()
        for line_num, import_line in import_lines:
            if import_line in seen_imports:
                self.issues['duplicated_imports'].append({
                    'file': file_path,
                    'line': line_num,
                    'import': import_line
                })
            seen_imports.add(import_line)
    
    def find_duplicated_code(self, files):
        """Encontra código duplicado usando análise de similaridade"""
        file_contents = {}
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_contents[file_path] = content
            except Exception:
                continue
        
        # Análise simples de similaridade
        files_list = list(file_contents.items())
        for i, (file1, content1) in enumerate(files_list):
            for j, (file2, content2) in enumerate(files_list[i+1:], i+1):
                similarity = self._calculate_similarity(content1, content2)
                if similarity > 0.8:  # 80% de similaridade
                    self.duplicated_code.append({
                        'file1': file1,
                        'file2': file2,
                        'similarity': similarity,
                        'severity': 'MEDIUM'
                    })
    
    def _calculate_similarity(self, content1, content2):
        """Calcula similaridade entre dois conteúdos"""
        lines1 = set(content1.split('\n'))
        lines2 = set(content2.split('\n'))
        
        intersection = len(lines1.intersection(lines2))
        union = len(lines1.union(lines2))
        
        return intersection / union if union > 0 else 0
    
    def generate_report(self):
        """Gera relatório de qualidade"""
        report = []
        report.append("# 📊 RELATÓRIO DE QUALIDADE DE CÓDIGO")
        report.append("=" * 50)
        report.append(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append()
        
        # Resumo
        total_issues = (len(self.exceptions_issues) + len(self.global_vars) + 
                       len(self.logging_issues) + len(self.docstring_issues) + 
                       len(self.duplicated_code))
        
        report.append(f"📈 **RESUMO GERAL**")
        report.append(f"- Total de problemas encontrados: {total_issues}")
        report.append(f"- Exceções inadequadas: {len(self.exceptions_issues)}")
        report.append(f"- Variáveis globais: {len(self.global_vars)}")
        report.append(f"- Logging inadequado: {len(self.logging_issues)}")
        report.append(f"- Docstrings ausentes: {len(self.docstring_issues)}")
        report.append(f"- Código duplicado: {len(self.duplicated_code)}")
        report.append()
        
        # Exceções
        if self.exceptions_issues:
            report.append("🚨 **EXCEÇÕES INADEQUADAS**")
            for issue in self.exceptions_issues:
                report.append(f"- {issue['file']}:{issue['line']} - {issue['issue']}")
            report.append()
        
        # Variáveis globais
        if self.global_vars:
            report.append("🌐 **VARIÁVEIS GLOBAIS**")
            for var in self.global_vars:
                report.append(f"- {var['file']}:{var['line']} - {var['variable']}")
            report.append()
        
        # Logging
        if self.logging_issues:
            report.append("📝 **LOGGING INADEQUADO**")
            for issue in self.logging_issues:
                report.append(f"- {issue['file']}:{issue['line']} - {issue['operation']}")
            report.append()
        
        # Docstrings
        if self.docstring_issues:
            report.append("📚 **DOCSTRINGS AUSENTES**")
            for issue in self.docstring_issues[:10]:  # Limitar a 10
                report.append(f"- {issue['file']}:{issue['line']} - {issue['name']} ({issue['type']})")
            if len(self.docstring_issues) > 10:
                report.append(f"... e mais {len(self.docstring_issues) - 10} itens")
            report.append()
        
        # Código duplicado
        if self.duplicated_code:
            report.append("🔄 **CÓDIGO DUPLICADO**")
            for dup in self.duplicated_code:
                report.append(f"- {dup['file1']} ↔ {dup['file2']} ({dup['similarity']:.1%})")
            report.append()
        
        return "\n".join(report)

def main():
    """Executa análise de qualidade"""
    print("🔍 ANÁLISE DE QUALIDADE DE CÓDIGO")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    analyzer = CodeQualityAnalyzer()
    
    # Encontrar arquivos Python
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Pular diretórios desnecessários
        dirs[:] = [d for d in dirs if d not in ['venv', 'node_modules', '__pycache__', '.git', 'backup_antes_limpeza_*']]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('.'):
                python_files.append(os.path.join(root, file))
    
    print(f"📁 Analisando {len(python_files)} arquivos Python...")
    
    # Analisar cada arquivo
    for file_path in python_files:
        analyzer.analyze_file(file_path)
    
    # Encontrar código duplicado
    print("🔄 Verificando código duplicado...")
    analyzer.find_duplicated_code(python_files)
    
    # Gerar relatório
    report = analyzer.generate_report()
    
    # Salvar relatório
    with open('relatorio_qualidade_codigo.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Análise concluída!")
    print("📄 Relatório salvo em: relatorio_qualidade_codigo.md")
    print()
    print(report)

if __name__ == "__main__":
    main()
