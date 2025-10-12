"""
Módulo de Segurança de Autenticação
===================================

Implementa controles avançados de autenticação:
- Regeneração de sessão após login (anti-fixation)
- Account lockout progressivo
- 2FA com TOTP
- Rate limiting por IP e usuário
"""
import secrets
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional
from flask import current_app, session, request
from functools import wraps


class AccountLockout:
    """
    Gerenciador de bloqueio de conta progressivo
    
    Lógica:
    - 3 tentativas: aviso
    - 5 tentativas: lockout 5 minutos
    - 10 tentativas: lockout 30 minutos
    - 15+ tentativas: lockout permanente (requer admin)
    """
    
    @staticmethod
    def get_lockout_key(username: str, ip_address: str) -> str:
        """Gera chave Redis para lockout"""
        return f"lockout:{username}:{ip_address}"
    
    @staticmethod
    def record_failed_attempt(username: str, ip_address: str) -> Tuple[bool, str, int]:
        """
        Registra tentativa de login falha
        
        Returns:
            (is_locked, message, attempts)
        """
        try:
            from meu_app import flask_cache as cache
            
            key = AccountLockout.get_lockout_key(username, ip_address)
            attempts = cache.get(key) or 0
            attempts += 1
            
            # Determinar tempo de lockout
            if attempts >= 15:
                # Lockout permanente
                cache.set(key, attempts, timeout=86400 * 30)  # 30 dias
                return True, "Conta bloqueada por excesso de tentativas. Contate o administrador.", attempts
            
            elif attempts >= 10:
                # Lockout 30 minutos
                cache.set(key, attempts, timeout=1800)
                return True, "Muitas tentativas de login. Conta bloqueada por 30 minutos.", attempts
            
            elif attempts >= 5:
                # Lockout 5 minutos
                cache.set(key, attempts, timeout=300)
                return True, "Muitas tentativas de login. Conta bloqueada por 5 minutos.", attempts
            
            elif attempts >= 3:
                # Aviso
                cache.set(key, attempts, timeout=300)
                return False, f"Senha incorreta. {5 - attempts} tentativas restantes antes do bloqueio.", attempts
            
            else:
                # Primeiras tentativas
                cache.set(key, attempts, timeout=300)
                return False, "Usuário ou senha inválidos.", attempts
            
        except Exception as e:
            current_app.logger.error(f"Erro em record_failed_attempt: {e}")
            return False, "Usuário ou senha inválidos.", 0
    
    @staticmethod
    def is_locked(username: str, ip_address: str) -> Tuple[bool, str]:
        """
        Verifica se usuário está bloqueado
        
        Returns:
            (is_locked, message)
        """
        try:
            from meu_app import flask_cache as cache
            
            key = AccountLockout.get_lockout_key(username, ip_address)
            attempts = cache.get(key) or 0
            
            if attempts >= 15:
                return True, "Conta bloqueada permanentemente. Contate o administrador."
            elif attempts >= 10:
                return True, "Conta temporariamente bloqueada. Tente novamente em 30 minutos."
            elif attempts >= 5:
                return True, "Conta temporariamente bloqueada. Tente novamente em 5 minutos."
            
            return False, ""
            
        except Exception as e:
            current_app.logger.error(f"Erro em is_locked: {e}")
            return False, ""
    
    @staticmethod
    def reset_attempts(username: str, ip_address: str):
        """Reseta tentativas após login bem-sucedido"""
        try:
            from meu_app import flask_cache as cache
            
            key = AccountLockout.get_lockout_key(username, ip_address)
            cache.delete(key)
            
            current_app.logger.info(f"Tentativas resetadas para {username}")
            
        except Exception as e:
            current_app.logger.error(f"Erro em reset_attempts: {e}")


class SessionSecurity:
    """Gerenciador de segurança de sessão"""
    
    @staticmethod
    def regenerate_session():
        """
        Regenera ID de sessão (previne session fixation)
        
        IMPORTANTE: Chamar após login bem-sucedido
        """
        # Salvar dados atuais
        data = {key: session[key] for key in session.keys()}
        
        # Limpar sessão antiga
        session.clear()
        
        # Gerar novo session ID (Flask faz isso automaticamente ao modificar)
        session.modified = True
        
        # Restaurar dados
        for key, value in data.items():
            session[key] = value
        
        # Adicionar token de sessão único
        session['_session_token'] = secrets.token_hex(32)
        session['_session_created_at'] = datetime.utcnow().isoformat()
        
        current_app.logger.info("Sessão regenerada após login")
    
    @staticmethod
    def validate_session() -> bool:
        """
        Valida se sessão ainda é válida
        
        Returns:
            True se válida, False caso contrário
        """
        # Verificar token de sessão
        if '_session_token' not in session:
            return False
        
        # Verificar tempo de criação
        if '_session_created_at' in session:
            created_at = datetime.fromisoformat(session['_session_created_at'])
            max_age = timedelta(hours=8)  # Configurável
            
            if datetime.utcnow() - created_at > max_age:
                current_app.logger.warning("Sessão expirada por idade")
                return False
        
        return True
    
    @staticmethod
    def add_security_headers():
        """Adiciona headers de segurança específicos de sessão"""
        # Já implementado em __init__.py após request
        pass


class TwoFactorAuth:
    """
    Gerenciador de autenticação de dois fatores (2FA)
    Usa TOTP (Time-based One-Time Password)
    """
    
    @staticmethod
    def generate_secret() -> str:
        """Gera secret para TOTP"""
        import pyotp
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(username: str, secret: str) -> str:
        """
        Gera QR code para configuração no app autenticador
        
        Returns:
            URI do QR code
        """
        import pyotp
        
        app_name = current_app.config.get('TOTP_APP_NAME', 'SAP-Sistema')
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=app_name)
    
    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """
        Verifica token TOTP
        
        Args:
            secret: Secret do usuário
            token: Token de 6 dígitos informado
            
        Returns:
            True se válido, False caso contrário
        """
        import pyotp
        
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Aceita 1 intervalo antes/depois
    
    @staticmethod
    def is_enabled_for_user(user_id: int) -> bool:
        """Verifica se 2FA está habilitado para o usuário"""
        from meu_app.models import Usuario
        from meu_app import db
        
        usuario = db.session.get(Usuario, user_id)
        return usuario and usuario.totp_secret is not None
    
    @staticmethod
    def enable_2fa(user_id: int) -> Tuple[bool, str, str]:
        """
        Habilita 2FA para usuário
        
        Returns:
            (success, message, qr_uri)
        """
        from meu_app.models import Usuario
        from meu_app import db
        
        try:
            usuario = db.session.get(Usuario, user_id)
            if not usuario:
                return False, "Usuário não encontrado", ""
            
            # Gerar secret
            secret = TwoFactorAuth.generate_secret()
            qr_uri = TwoFactorAuth.generate_qr_code(usuario.nome, secret)
            
            # Salvar secret (ainda não ativo até verificar)
            usuario.totp_secret = secret
            usuario.totp_enabled = False
            db.session.commit()
            
            return True, "2FA configurado. Escaneie o QR code e verifique.", qr_uri
            
        except Exception as e:
            current_app.logger.error(f"Erro ao habilitar 2FA: {e}")
            db.session.rollback()
            return False, str(e), ""
    
    @staticmethod
    def verify_and_activate_2fa(user_id: int, token: str) -> Tuple[bool, str]:
        """
        Verifica token e ativa 2FA
        
        Args:
            user_id: ID do usuário
            token: Token de 6 dígitos para verificação inicial
            
        Returns:
            (success, message)
        """
        from meu_app.models import Usuario
        from meu_app import db
        
        try:
            usuario = db.session.get(Usuario, user_id)
            if not usuario or not usuario.totp_secret:
                return False, "Erro na configuração do 2FA"
            
            # Verificar token
            if not TwoFactorAuth.verify_token(usuario.totp_secret, token):
                return False, "Token inválido. Tente novamente."
            
            # Ativar 2FA
            usuario.totp_enabled = True
            db.session.commit()
            
            current_app.logger.info(f"2FA ativado para usuário {usuario.nome}")
            return True, "2FA ativado com sucesso!"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao ativar 2FA: {e}")
            db.session.rollback()
            return False, str(e)


def requires_2fa_verification(f):
    """
    Decorador que requer verificação 2FA se habilitado
    
    Uso:
        @requires_2fa_verification
        def rota_protegida():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('main.login'))
        
        # Verificar se 2FA está habilitado para o usuário
        user_id = session['usuario_id']
        if TwoFactorAuth.is_enabled_for_user(user_id):
            # Verificar se já passou pela verificação 2FA nesta sessão
            if not session.get('_2fa_verified'):
                from flask import redirect, url_for
                return redirect(url_for('main.verify_2fa'))
        
        return f(*args, **kwargs)
    return decorated_function


__all__ = [
    'AccountLockout',
    'SessionSecurity',
    'TwoFactorAuth',
    'requires_2fa_verification',
]

