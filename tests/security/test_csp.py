"""
Testes de Content Security Policy (CSP)
=======================================

Verifica se os headers CSP estão configurados corretamente
e se os nonces estão sendo gerados e injetados.
"""
import pytest
import re
from flask import g


class TestCSPHeaders:
    """Testes de headers CSP"""
    
    def test_csp_header_presente(self, client, app):
        """Verifica se header CSP está presente nas respostas"""
        with client:
            response = client.get('/')
            assert 'Content-Security-Policy' in response.headers, "CSP header deve estar presente"
    
    def test_csp_sem_unsafe_inline_producao(self, app):
        """Verifica ausência de unsafe-inline em produção"""
        from config import ProductionConfig
        
        # Verificar configuração de produção
        csp = ProductionConfig.CSP_DIRECTIVES
        
        # Script-src não deve ter unsafe-inline
        assert "'unsafe-inline'" not in csp.get('script-src', []), \
            "script-src não deve conter unsafe-inline em produção"
        
        # Style-src não deve ter unsafe-inline
        assert "'unsafe-inline'" not in csp.get('style-src', []), \
            "style-src não deve conter unsafe-inline em produção"
        
        # Não deve ter unsafe-eval
        for directive in csp.values():
            if isinstance(directive, list):
                assert "'unsafe-eval'" not in directive, \
                    "Nenhuma diretiva deve conter unsafe-eval"
    
    def test_csp_nonce_unico_por_request(self, client):
        """Verifica se nonce é único para cada request"""
        with client:
            response1 = client.get('/login')
            response2 = client.get('/login')
            
            csp1 = response1.headers.get('Content-Security-Policy', '')
            csp2 = response2.headers.get('Content-Security-Policy', '')
            
            # Extrair nonces (formato: 'nonce-XXXX')
            nonces1 = re.findall(r"'nonce-([^']+)'", csp1)
            nonces2 = re.findall(r"'nonce-([^']+)'", csp2)
            
            if nonces1 and nonces2:
                assert nonces1[0] != nonces2[0], "Nonces devem ser únicos por request"
    
    def test_csp_strict_dynamic_presente(self, app):
        """Verifica se strict-dynamic está presente em produção"""
        from config import ProductionConfig
        
        csp = ProductionConfig.CSP_DIRECTIVES
        script_src = csp.get('script-src', [])
        
        assert "'strict-dynamic'" in script_src, \
            "script-src deve conter 'strict-dynamic' em produção"
    
    def test_csp_form_action_restrito(self, app):
        """Verifica se form-action está restrito a self"""
        from config import ProductionConfig
        
        csp = ProductionConfig.CSP_DIRECTIVES
        form_action = csp.get('form-action', [])
        
        assert ["'self'"] == form_action, \
            "form-action deve estar restrito a 'self'"
    
    def test_csp_upgrade_insecure_requests(self, app):
        """Verifica se upgrade-insecure-requests está presente"""
        from config import ProductionConfig
        
        csp = ProductionConfig.CSP_DIRECTIVES
        
        assert 'upgrade-insecure-requests' in csp, \
            "upgrade-insecure-requests deve estar presente"
    
    def test_csp_block_mixed_content(self, app):
        """Verifica se block-all-mixed-content está presente"""
        from config import ProductionConfig
        
        csp = ProductionConfig.CSP_DIRECTIVES
        
        assert 'block-all-mixed-content' in csp, \
            "block-all-mixed-content deve estar presente"


class TestSecurityHeaders:
    """Testes de headers de segurança adicionais"""
    
    def test_x_content_type_options(self, app):
        """Verifica header X-Content-Type-Options"""
        from config import ProductionConfig
        
        headers = ProductionConfig.SECURITY_HEADERS
        assert headers.get('X-Content-Type-Options') == 'nosniff', \
            "X-Content-Type-Options deve ser 'nosniff'"
    
    def test_x_frame_options(self, app):
        """Verifica header X-Frame-Options"""
        from config import ProductionConfig
        
        headers = ProductionConfig.SECURITY_HEADERS
        assert headers.get('X-Frame-Options') == 'DENY', \
            "X-Frame-Options deve ser 'DENY'"
    
    def test_referrer_policy(self, app):
        """Verifica Referrer-Policy"""
        from config import ProductionConfig
        
        headers = ProductionConfig.SECURITY_HEADERS
        assert 'Referrer-Policy' in headers, \
            "Referrer-Policy deve estar presente"
    
    def test_permissions_policy(self, app):
        """Verifica Permissions-Policy"""
        from config import ProductionConfig
        
        headers = ProductionConfig.SECURITY_HEADERS
        assert 'Permissions-Policy' in headers, \
            "Permissions-Policy deve estar presente"
        
        # Verificar que recursos perigosos estão desabilitados
        policy = headers['Permissions-Policy']
        assert 'geolocation=()' in policy, "geolocation deve estar desabilitado"
        assert 'microphone=()' in policy, "microphone deve estar desabilitado"
        assert 'camera=()' in policy, "camera deve estar desabilitado"
    
    def test_cross_origin_headers(self, app):
        """Verifica headers COOP/COEP/CORP"""
        from config import ProductionConfig
        
        headers = ProductionConfig.SECURITY_HEADERS
        
        assert headers.get('Cross-Origin-Opener-Policy') == 'same-origin', \
            "COOP deve ser 'same-origin'"
        
        assert headers.get('Cross-Origin-Embedder-Policy') == 'require-corp', \
            "COEP deve ser 'require-corp'"
        
        assert headers.get('Cross-Origin-Resource-Policy') == 'same-origin', \
            "CORP deve ser 'same-origin'"


class TestHTTPS:
    """Testes de configuração HTTPS"""
    
    def test_force_https_producao(self, app):
        """Verifica se FORCE_HTTPS está habilitado em produção"""
        from config import ProductionConfig
        
        assert ProductionConfig.FORCE_HTTPS is True, \
            "FORCE_HTTPS deve ser True em produção"
    
    def test_hsts_enabled_producao(self, app):
        """Verifica se HSTS está habilitado em produção"""
        from config import ProductionConfig
        
        assert ProductionConfig.HSTS_ENABLED is True, \
            "HSTS_ENABLED deve ser True em produção"
    
    def test_hsts_max_age(self, app):
        """Verifica HSTS max-age (deve ser 1 ano)"""
        from config import ProductionConfig
        
        expected_max_age = 31536000  # 1 ano em segundos
        assert ProductionConfig.HSTS_MAX_AGE == expected_max_age, \
            f"HSTS_MAX_AGE deve ser {expected_max_age} (1 ano)"
    
    def test_hsts_include_subdomains(self, app):
        """Verifica se HSTS inclui subdomínios"""
        from config import ProductionConfig
        
        assert ProductionConfig.HSTS_INCLUDE_SUBDOMAINS is True, \
            "HSTS_INCLUDE_SUBDOMAINS deve ser True"
    
    def test_hsts_preload(self, app):
        """Verifica se HSTS preload está habilitado"""
        from config import ProductionConfig
        
        assert ProductionConfig.HSTS_PRELOAD is True, \
            "HSTS_PRELOAD deve ser True"


class TestCacheControl:
    """Testes de Cache-Control para rotas autenticadas"""
    
    @pytest.mark.skip(reason="Requer autenticação mock")
    def test_cache_control_rotas_autenticadas(self, client, authenticated_user):
        """Verifica se Cache-Control está configurado para rotas autenticadas"""
        with client:
            # Fazer login
            client.post('/login', data={
                'usuario': 'admin',
                'senha': 'admin123',
                'csrf_token': 'test'
            })
            
            # Acessar rota autenticada
            response = client.get('/painel')
            
            # Verificar headers de cache
            assert response.headers.get('Cache-Control') == 'no-store, no-cache, must-revalidate, private', \
                "Cache-Control deve estar configurado para rotas autenticadas"
            
            assert response.headers.get('Pragma') == 'no-cache', \
                "Pragma deve ser 'no-cache'"
            
            assert response.headers.get('Expires') == '0', \
                "Expires deve ser '0'"


class TestNonceInjection:
    """Testes de injeção de nonce nos templates"""
    
    def test_nonce_disponivel_no_context(self, app, client):
        """Verifica se nonce está disponível no contexto dos templates"""
        with client:
            with app.test_request_context('/'):
                from flask import g, render_template_string
                
                # Gerar nonce
                from meu_app.security import _register_nonce_context_processor
                
                # Simular contexto
                template = "{{ nonce }}"
                rendered = render_template_string(template)
                
                # Nonce deve existir e não estar vazio
                assert rendered, "Nonce deve estar disponível no contexto"
                assert len(rendered) > 0, "Nonce não deve estar vazio"
    
    def test_nonce_formato_valido(self, client):
        """Verifica se nonce tem formato válido (base64url)"""
        with client:
            response = client.get('/login')
            csp = response.headers.get('Content-Security-Policy', '')
            
            # Extrair nonce
            nonces = re.findall(r"'nonce-([^']+)'", csp)
            
            if nonces:
                nonce = nonces[0]
                # Verificar formato base64url (apenas caracteres válidos)
                assert re.match(r'^[A-Za-z0-9_-]+$', nonce), \
                    "Nonce deve ter formato base64url válido"
                
                # Verificar comprimento mínimo (16 bytes = ~22 chars em base64)
                assert len(nonce) >= 20, \
                    "Nonce deve ter comprimento mínimo de 20 caracteres"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

