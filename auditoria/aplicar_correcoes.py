#!/usr/bin/env python3
"""
Script para aplicar correções de segurança automaticamente
Reduz o nível de risco de MÉDIO para BAIXO
"""

import os
import sys
from pathlib import Path

class SecurityPatcher:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.changes = []
        
    def check_flask_wtf(self):
        """Verifica se Flask-WTF está instalado"""
        try:
            import flask_wtf
            print("✅ Flask-WTF já está instalado")
            return True
        except ImportError:
            print("❌ Flask-WTF não encontrado")
            print("   Execute: pip install Flask-WTF")
            return False
    
    def check_current_nonce_implementation(self):
        """Verifica implementação atual do nonce"""
        init_file = self.base_path / 'meu_app' / '__init__.py'
        
        with open(init_file, 'r') as f:
            content = f.read()
        
        has_nonce_generation = 'generate_nonce' in content or 'g.nonce' in content
        has_context_processor = 'inject_nonce' in content or 'context_processor' in content
        
        print("\n📋 Verificação de Nonce:")
        print(f"   Geração de nonce: {'✅' if has_nonce_generation else '❌'}")
        print(f"   Context processor: {'✅' if has_context_processor else '❌'}")
        
        return has_nonce_generation and has_context_processor
    
    def check_csrf_protection(self):
        """Verifica se CSRF está ativo"""
        init_file = self.base_path / 'meu_app' / '__init__.py'
        
        with open(init_file, 'r') as f:
            content = f.read()
        
        has_csrf_import = 'CSRFProtect' in content
        has_csrf_init = 'csrf.init_app' in content or 'CSRFProtect(app)' in content
        
        print("\n📋 Verificação de CSRF:")
        print(f"   Import CSRFProtect: {'✅' if has_csrf_import else '❌'}")
        print(f"   CSRF inicializado: {'✅' if has_csrf_init else '❌'}")
        
        return has_csrf_import and has_csrf_init
    
    def find_forms_without_csrf(self):
        """Encontra formulários sem CSRF token"""
        templates_dir = self.base_path / 'meu_app' / 'templates'
        forms_without_csrf = []
        
        for html_file in templates_dir.rglob('*.html'):
            with open(html_file, 'r') as f:
                content = f.read()
            
            # Verificar se tem form POST
            if '<form' in content and 'method=' in content.lower():
                # Verificar se não tem csrf_token
                if 'csrf_token' not in content and 'form.hidden_tag' not in content:
                    forms_without_csrf.append(str(html_file.relative_to(self.base_path)))
        
        return forms_without_csrf
    
    def generate_recommendations(self):
        """Gera recomendações baseadas na análise"""
        print("\n" + "="*70)
        print("📊 ANÁLISE DE SEGURANÇA - RECOMENDAÇÕES")
        print("="*70)
        
        # 1. Flask-WTF
        flask_wtf_ok = self.check_flask_wtf()
        
        # 2. Nonce
        nonce_ok = self.check_current_nonce_implementation()
        
        # 3. CSRF
        csrf_ok = self.check_csrf_protection()
        
        # 4. Formulários
        print("\n📋 Verificação de Formulários:")
        forms_missing = self.find_forms_without_csrf()
        if forms_missing:
            print(f"   ⚠️  {len(forms_missing)} formulário(s) sem CSRF token:")
            for form in forms_missing[:10]:  # Top 10
                print(f"      - {form}")
        else:
            print("   ✅ Todos os formulários têm CSRF token")
        
        # Resumo
        print("\n" + "="*70)
        print("📝 RESUMO DE AÇÕES NECESSÁRIAS")
        print("="*70)
        
        actions_needed = []
        
        if not flask_wtf_ok:
            actions_needed.append({
                'priority': '🔴 ALTA',
                'action': 'Instalar Flask-WTF',
                'command': 'pip install Flask-WTF'
            })
        
        if not nonce_ok:
            actions_needed.append({
                'priority': '🔴 ALTA',
                'action': 'Implementar geração dinâmica de nonce',
                'command': 'Ver: auditoria/PLANO_ACAO_RISCO_BAIXO.md (Seção 1)'
            })
        
        if not csrf_ok:
            actions_needed.append({
                'priority': '🟡 MÉDIA',
                'action': 'Configurar CSRFProtect globalmente',
                'command': 'Ver: auditoria/PLANO_ACAO_RISCO_BAIXO.md (Seção 2)'
            })
        
        if forms_missing:
            actions_needed.append({
                'priority': '🟡 MÉDIA',
                'action': f'Adicionar CSRF token em {len(forms_missing)} formulário(s)',
                'command': 'Adicionar: {{ csrf_token() }} ou {{ form.csrf_token }}'
            })
        
        if not actions_needed:
            print("\n✅ PARABÉNS! Todas as verificações passaram!")
            print("   Execute a auditoria novamente para confirmar:")
            print("   $ python auditoria/security_audit.py")
            return True
        
        for i, action in enumerate(actions_needed, 1):
            print(f"\n{i}. {action['priority']} - {action['action']}")
            print(f"   💻 {action['command']}")
        
        print("\n" + "="*70)
        print("📚 DOCUMENTAÇÃO COMPLETA:")
        print("   📖 auditoria/PLANO_ACAO_RISCO_BAIXO.md")
        print("="*70)
        
        return False
    
    def test_csrf_protection(self):
        """Testa se CSRF está funcionando"""
        print("\n🧪 TESTANDO PROTEÇÃO CSRF...")
        
        try:
            sys.path.insert(0, str(self.base_path))
            from meu_app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                # Tentar POST sem CSRF
                response = client.post('/login', data={
                    'usuario': 'teste',
                    'senha': 'teste'
                }, follow_redirects=False)
                
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code in [400, 403]:
                    print("   ✅ CSRF está ATIVO e bloqueando requests inválidos!")
                    return True
                else:
                    print("   ⚠️  CSRF pode não estar ativo ou rota está isenta")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Erro ao testar: {e}")
            return False

def main():
    base_path = Path('/Users/ericobrandao/Projects/GERPED')
    
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     🔒 ANÁLISE DE CORREÇÕES DE SEGURANÇA - Sistema GERPED       ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    patcher = SecurityPatcher(base_path)
    
    # Gerar recomendações
    all_ok = patcher.generate_recommendations()
    
    # Testar CSRF
    if all_ok:
        patcher.test_csrf_protection()
    
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                    🎯 PRÓXIMOS PASSOS                         ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print("1. Ler o plano de ação completo:")
    print("   $ cat auditoria/PLANO_ACAO_RISCO_BAIXO.md")
    print()
    print("2. Aplicar as correções manualmente seguindo o guia")
    print()
    print("3. Executar nova auditoria:")
    print("   $ python auditoria/security_audit.py")
    print()
    print("4. Verificar nível de risco: deve ser 🟢 BAIXO")
    print()

if __name__ == '__main__':
    main()

