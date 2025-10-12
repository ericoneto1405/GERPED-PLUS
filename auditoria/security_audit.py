#!/usr/bin/env python3
"""
Script de Auditoria de Segurança - Sistema SAP
Analisa o código fonte em busca de vulnerabilidades comuns
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class SecurityAuditor:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.vulnerabilities = []
        self.stats = defaultdict(int)
        
    def scan_file(self, file_path):
        """Escaneia um arquivo em busca de vulnerabilidades"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            relative_path = str(file_path.relative_to(self.base_path))
            
            # 1. SQL Injection
            self.check_sql_injection(content, lines, relative_path)
            
            # 2. XSS
            self.check_xss(content, lines, relative_path)
            
            # 3. CSRF
            self.check_csrf(content, lines, relative_path)
            
            # 4. Directory Traversal
            self.check_directory_traversal(content, lines, relative_path)
            
            # 5. Hardcoded Secrets
            self.check_hardcoded_secrets(content, lines, relative_path)
            
            # 6. Insecure Deserialization
            self.check_deserialization(content, lines, relative_path)
            
            # 7. Command Injection
            self.check_command_injection(content, lines, relative_path)
            
        except Exception as e:
            print(f"Erro ao escanear {file_path}: {e}")
    
    def check_sql_injection(self, content, lines, file_path):
        """Verifica SQL Injection"""
        # Padrões perigosos de concatenação SQL
        patterns = [
            (r'\.execute\([^)]*f["\']', 'SQL query com f-string (possível SQL Injection)', 'HIGH'),
            (r'\.execute\([^)]*\+', 'SQL query com concatenação de strings', 'HIGH'),
            (r'\.execute\([^)]*%[^)]*\)', 'SQL query com formatação de strings', 'MEDIUM'),
            (r'\.raw\(', 'Query raw SQL sem parametrização', 'MEDIUM'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line) and 'execute' in line.lower():
                    self.add_vulnerability(
                        name='SQL Injection',
                        endpoint=file_path,
                        line=i,
                        code_snippet=line.strip(),
                        severity=severity,
                        description=desc,
                        recommendation='Use parametrização de queries (prepared statements) em vez de concatenação de strings'
                    )
    
    def check_xss(self, content, lines, file_path):
        """Verifica XSS"""
        if file_path.endswith('.html'):
            # Templates sem auto-escape
            patterns = [
                (r'\{\{.*\|safe\}\}', 'Uso de |safe pode permitir XSS', 'MEDIUM'),
                (r'\{\{.*\|raw\}\}', 'Uso de |raw pode permitir XSS', 'MEDIUM'),
                (r'v-html=', 'v-html pode permitir XSS', 'MEDIUM'),
                (r'dangerouslySetInnerHTML', 'dangerouslySetInnerHTML pode permitir XSS', 'HIGH'),
            ]
        else:
            # Código Python que renderiza HTML
            patterns = [
                (r'render_template_string\(', 'render_template_string sem escape', 'MEDIUM'),
                (r'Markup\(', 'Uso de Markup() requer validação', 'LOW'),
            ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line):
                    self.add_vulnerability(
                        name='Cross-Site Scripting (XSS)',
                        endpoint=file_path,
                        line=i,
                        code_snippet=line.strip(),
                        severity=severity,
                        description=desc,
                        recommendation='Sempre escape dados do usuário antes de renderizar. Evite |safe e |raw a menos que necessário'
                    )
    
    def check_csrf(self, content, lines, file_path):
        """Verifica proteção CSRF"""
        if file_path.endswith('.py'):
            # Rotas POST sem verificação CSRF
            if 'methods=' in content and 'POST' in content:
                has_csrf_protect = '@csrf.exempt' in content or 'csrf_token' in content
                if not has_csrf_protect and 'Blueprint' in content:
                    for i, line in enumerate(lines, 1):
                        if 'methods=' in line and 'POST' in line:
                            self.add_vulnerability(
                                name='CSRF Token Missing',
                                endpoint=file_path,
                                line=i,
                                code_snippet=line.strip(),
                                severity='MEDIUM',
                                description='Rota POST sem verificação CSRF explícita',
                                recommendation='Implemente validação de CSRF token em todas as rotas POST'
                            )
                            break
    
    def check_directory_traversal(self, content, lines, file_path):
        """Verifica Directory Traversal"""
        patterns = [
            (r'open\([^)]*request\.|send_file\([^)]*request\.', 'Acesso a arquivo baseado em input do usuário', 'HIGH'),
            (r'os\.path\.join\([^)]*request\.', 'Path join com input do usuário', 'HIGH'),
            (r'\.read\([^)]*request\.', 'Leitura de arquivo com input do usuário', 'HIGH'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line):
                    self.add_vulnerability(
                        name='Directory Traversal',
                        endpoint=file_path,
                        line=i,
                        code_snippet=line.strip(),
                        severity=severity,
                        description=desc,
                        recommendation='Valide e sanitize paths. Use Path().resolve() e verifique se está dentro do diretório permitido'
                    )
    
    def check_hardcoded_secrets(self, content, lines, file_path):
        """Verifica credenciais hardcoded"""
        patterns = [
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'Senha hardcoded', 'HIGH'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'API key hardcoded', 'HIGH'),
            (r'secret\s*=\s*["\'][^"\']{10,}["\']', 'Secret hardcoded', 'HIGH'),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', 'Token hardcoded', 'HIGH'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Excluir exemplos e comentários
                    if not line.strip().startswith('#') and 'example' not in line.lower():
                        self.add_vulnerability(
                            name='Hardcoded Secrets',
                            endpoint=file_path,
                            line=i,
                            code_snippet='[REDACTED]',
                            severity=severity,
                            description=desc,
                            recommendation='Use variáveis de ambiente ou arquivos de configuração seguros para credenciais'
                        )
    
    def check_deserialization(self, content, lines, file_path):
        """Verifica deserialização insegura"""
        patterns = [
            (r'pickle\.load', 'pickle.load pode executar código arbitrário', 'HIGH'),
            (r'yaml\.load\([^,)]*\)', 'yaml.load sem SafeLoader', 'HIGH'),
            (r'eval\(', 'eval() pode executar código arbitrário', 'CRITICAL'),
            (r'exec\(', 'exec() pode executar código arbitrário', 'CRITICAL'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line):
                    self.add_vulnerability(
                        name='Insecure Deserialization',
                        endpoint=file_path,
                        line=i,
                        code_snippet=line.strip(),
                        severity=severity,
                        description=desc,
                        recommendation='Use métodos seguros de deserialização (json.loads, yaml.safe_load)'
                    )
    
    def check_command_injection(self, content, lines, file_path):
        """Verifica Command Injection"""
        patterns = [
            (r'os\.system\(', 'os.system() com input não validado', 'HIGH'),
            (r'subprocess\.call\([^)]*shell=True', 'subprocess com shell=True', 'HIGH'),
            (r'subprocess\.Popen\([^)]*shell=True', 'Popen com shell=True', 'HIGH'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc, severity in patterns:
                if re.search(pattern, line):
                    self.add_vulnerability(
                        name='Command Injection',
                        endpoint=file_path,
                        line=i,
                        code_snippet=line.strip(),
                        severity=severity,
                        description=desc,
                        recommendation='Evite shell=True. Use lista de argumentos e valide todos os inputs'
                    )
    
    def add_vulnerability(self, **kwargs):
        """Adiciona uma vulnerabilidade encontrada"""
        self.vulnerabilities.append(kwargs)
        self.stats[kwargs['severity']] += 1
    
    def scan_directory(self):
        """Escaneia todo o diretório"""
        # Extensões de arquivo para escanear
        extensions = {'.py', '.html', '.js', '.jsx', '.vue', '.ts', '.tsx'}
        
        # Diretórios para ignorar
        ignore_dirs = {'venv', 'node_modules', '__pycache__', '.git', 'migrations', 'static'}
        
        print("🔍 Iniciando varredura de segurança...")
        print(f"📂 Diretório base: {self.base_path}")
        print()
        
        files_scanned = 0
        for root, dirs, files in os.walk(self.base_path):
            # Remover diretórios ignorados
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = Path(root) / file
                    self.scan_file(file_path)
                    files_scanned += 1
        
        print(f"✅ {files_scanned} arquivos escaneados")
        return files_scanned
    
    def generate_report(self):
        """Gera relatórios HTML e JSON"""
        # Relatório JSON
        json_report = {
            'scan_date': datetime.now().isoformat(),
            'total_vulnerabilities': len(self.vulnerabilities),
            'by_severity': dict(self.stats),
            'vulnerabilities': self.vulnerabilities
        }
        
        json_path = self.base_path / 'auditoria' / 'pentest_zap_vulnerabilidades.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        
        # Relatório HTML
        html_content = self.generate_html_report(json_report)
        html_path = self.base_path / 'auditoria' / 'pentest_zap_relatorio.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Resumo JSON
        summary = {
            'scan_date': datetime.now().isoformat(),
            'total_alerts': len(self.vulnerabilities),
            'by_severity': dict(self.stats),
            'critical_vulnerabilities': [
                v for v in self.vulnerabilities 
                if v['severity'] in ['CRITICAL', 'HIGH']
            ][:20]  # Top 20
        }
        
        summary_path = self.base_path / 'auditoria' / 'pentest_zap_resumo.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return json_path, html_path, summary_path
    
    def generate_html_report(self, data):
        """Gera relatório HTML"""
        severity_colors = {
            'CRITICAL': '#dc3545',
            'HIGH': '#fd7e14',
            'MEDIUM': '#ffc107',
            'LOW': '#17a2b8',
            'INFO': '#6c757d'
        }
        
        vulns_by_severity = defaultdict(list)
        for vuln in self.vulnerabilities:
            vulns_by_severity[vuln['severity']].append(vuln)
        
        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Segurança - Sistema SAP</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1rem; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        .vulnerability-section {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .severity-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            color: white;
        }}
        .vuln-item {{
            border-left: 4px solid #e9ecef;
            padding: 20px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        .vuln-title {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .vuln-detail {{
            margin: 8px 0;
            color: #495057;
        }}
        .code-snippet {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            margin: 10px 0;
        }}
        .recommendation {{
            background: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-top: 10px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Relatório de Segurança</h1>
            <p>Sistema SAP - Auditoria de Código Fonte</p>
            <p>Data: {data['scan_date']}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{data['total_vulnerabilities']}</div>
                <div class="stat-label">Total de Vulnerabilidades</div>
            </div>
"""
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            count = data['by_severity'].get(severity, 0)
            color = severity_colors.get(severity, '#6c757d')
            html += f"""
            <div class="stat-card">
                <div class="stat-value" style="color: {color};">{count}</div>
                <div class="stat-label">{severity}</div>
            </div>
"""
        
        html += """
        </div>
"""
        
        # Vulnerabilidades por severidade
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            vulns = vulns_by_severity.get(severity, [])
            if vulns:
                color = severity_colors[severity]
                html += f"""
        <div class="vulnerability-section">
            <h2 style="color: {color}; margin-bottom: 20px;">
                {severity} - {len(vulns)} vulnerabilidade(s)
            </h2>
"""
                for vuln in vulns:
                    html += f"""
            <div class="vuln-item" style="border-left-color: {color};">
                <div class="vuln-title">{vuln['name']}</div>
                <div class="vuln-detail"><strong>Arquivo:</strong> {vuln['endpoint']}</div>
                <div class="vuln-detail"><strong>Linha:</strong> {vuln.get('line', 'N/A')}</div>
                <div class="vuln-detail"><strong>Descrição:</strong> {vuln['description']}</div>
                <div class="code-snippet">{vuln.get('code_snippet', 'N/A')}</div>
                <div class="recommendation">
                    <strong>💡 Recomendação:</strong> {vuln['recommendation']}
                </div>
            </div>
"""
                html += """
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def print_summary(self):
        """Imprime resumo executivo"""
        print("\n" + "="*60)
        print("📊 RESUMO EXECUTIVO - AUDITORIA DE SEGURANÇA")
        print("="*60)
        print(f"\n📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔍 Total de Vulnerabilidades: {len(self.vulnerabilities)}\n")
        
        print("📊 Distribuição por Severidade:")
        severity_icons = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🔵',
            'INFO': '⚪'
        }
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            count = self.stats.get(severity, 0)
            icon = severity_icons.get(severity, '⚪')
            print(f"   {icon} {severity:10s}: {count:3d} vulnerabilidade(s)")
        
        # Top vulnerabilidades críticas
        critical = [v for v in self.vulnerabilities if v['severity'] in ['CRITICAL', 'HIGH']]
        if critical:
            print(f"\n🚨 TOP VULNERABILIDADES CRÍTICAS ({len(critical)}):")
            for i, vuln in enumerate(critical[:10], 1):
                print(f"\n{i}. {vuln['name']} [{vuln['severity']}]")
                print(f"   📁 {vuln['endpoint']}:{vuln.get('line', 'N/A')}")
                print(f"   📝 {vuln['description']}")
        else:
            print("\n✅ Nenhuma vulnerabilidade CRÍTICA ou HIGH detectada!")
        
        print("\n" + "="*60)

if __name__ == '__main__':
    # Caminho base do projeto
    base_path = Path('/Users/ericobrandao/Projects/SAP')
    
    # Criar auditor
    auditor = SecurityAuditor(base_path)
    
    # Escanear
    auditor.scan_directory()
    
    # Gerar relatórios
    json_path, html_path, summary_path = auditor.generate_report()
    
    # Imprimir resumo
    auditor.print_summary()
    
    print(f"\n📄 Relatórios gerados:")
    print(f"   - HTML: {html_path}")
    print(f"   - JSON: {json_path}")
    print(f"   - Resumo: {summary_path}")
    print("\n✅ Auditoria concluída!\n")

