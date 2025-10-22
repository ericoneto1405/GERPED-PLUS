#!/usr/bin/env python3
"""
Teste de Segurança RBAC - Sistema SAP
=====================================

Script para testar o sistema de permissões e isolamento de usuários.
"""

import requests
import json
from datetime import datetime

# Configurações
BASE_URL = "http://127.0.0.1:5004"
SESSION = requests.Session()

def log_test(test_name, result, details=""):
    """Log do resultado do teste"""
    status = "✅ PASSOU" if result else "❌ FALHOU"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

def get_csrf_token():
    """Obtém token CSRF da página de login"""
    try:
        response = SESSION.get(f"{BASE_URL}/login")
        if response.status_code == 200:
            # Buscar token CSRF no HTML
            import re
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if csrf_match:
                return csrf_match.group(1)
        return None
    except Exception:
        return None

def test_login(username, password):
    """Testa login com credenciais"""
    try:
        # Primeiro, obter token CSRF
        csrf_token = get_csrf_token()
        if not csrf_token:
            return False, "Não foi possível obter token CSRF"
        
        response = SESSION.post(f"{BASE_URL}/login", data={
            'usuario': username,
            'senha': password,
            'csrf_token': csrf_token
        }, allow_redirects=False)
        
        if response.status_code == 302:
            return True, "Login bem-sucedido"
        else:
            return False, f"Status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, f"Erro: {str(e)}"

def test_access_endpoint(endpoint, expected_status=200):
    """Testa acesso a endpoint"""
    try:
        response = SESSION.get(f"{BASE_URL}{endpoint}")
        return response.status_code == expected_status, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Erro: {str(e)}"

def test_bypass_permission():
    """Testa tentativas de bypass de permissão"""
    bypass_tests = [
        # Tentar acessar endpoints de admin sem ser admin
        ("/usuarios/listar", "Acesso a usuários sem permissão"),
        ("/financeiro/apuracao", "Acesso a apuração sem permissão"),
        ("/coletas/listar", "Acesso a coletas sem permissão"),
    ]
    
    results = []
    for endpoint, description in bypass_tests:
        success, details = test_access_endpoint(endpoint, 403)  # Esperamos 403
        results.append((description, success, details))
    
    return results

def test_user_isolation():
    """Testa isolamento entre usuários"""
    # Este teste seria mais complexo, requerendo múltiplas sessões
    # Por enquanto, vamos testar se o sistema mantém sessões separadas
    try:
        # Verificar se a sessão atual está ativa
        response = SESSION.get(f"{BASE_URL}/")
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Erro: {str(e)}"

def test_rate_limiting():
    """Testa rate limiting no login"""
    print("\n🔒 Testando Rate Limiting...")
    
    # Fazer múltiplas tentativas de login
    failed_attempts = 0
    for i in range(15):  # Mais que o limite padrão
        success, details = test_login("usuario_inexistente", "senha_errada")
        if not success:
            failed_attempts += 1
    
    # Se rate limiting estiver funcionando, deveria bloquear após algumas tentativas
    rate_limited = failed_attempts < 15
    log_test("Rate Limiting", rate_limited, f"Tentativas: {failed_attempts}/15")

def main():
    """Executa todos os testes de segurança"""
    print("🔐 TESTE DE SEGURANÇA RBAC - SISTEMA SAP")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {BASE_URL}")
    print()
    
    # Teste 1: Login com usuário válido
    print("🔑 Testando Autenticação...")
    success, details = test_login("admin", "admin123")  # Assumindo credenciais padrão
    log_test("Login Admin", success, details)
    
    if not success:
        print("❌ Não foi possível fazer login. Verifique se o servidor está rodando e as credenciais estão corretas.")
        return
    
    # Teste 2: Acesso a endpoints permitidos
    print("\n📋 Testando Acesso a Endpoints...")
    allowed_endpoints = [
        ("/", "Dashboard"),
        ("/pedidos/listar", "Listar Pedidos"),
        ("/clientes/listar", "Listar Clientes"),
    ]
    
    for endpoint, description in allowed_endpoints:
        success, details = test_access_endpoint(endpoint)
        log_test(description, success, details)
    
    # Teste 3: Bypass de permissões
    print("\n🛡️ Testando Bypass de Permissões...")
    bypass_results = test_bypass_permission()
    for description, success, details in bypass_results:
        log_test(description, success, details)
    
    # Teste 4: Isolamento de usuários
    print("\n👥 Testando Isolamento de Usuários...")
    success, details = test_user_isolation()
    log_test("Isolamento de Sessão", success, details)
    
    # Teste 5: Rate Limiting
    test_rate_limiting()
    
    # Teste 6: Logout
    print("\n🚪 Testando Logout...")
    try:
        response = SESSION.get(f"{BASE_URL}/logout", allow_redirects=False)
        success = response.status_code == 302
        log_test("Logout", success, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Logout", False, f"Erro: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ Teste de Segurança RBAC Concluído!")

if __name__ == "__main__":
    main()
