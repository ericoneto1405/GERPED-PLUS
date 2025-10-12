"""
Módulo de Masking de PII (Personally Identifiable Information)
================================================================

Protege dados sensíveis em logs e responses
"""
import re
from typing import Any, Dict
from flask import current_app


class PIIMasker:
    """Classe para masking de dados sensíveis"""
    
    # Padrões regex para detecção de PII
    PATTERNS = {
        'cpf': re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'),
        'cnpj': re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'telefone': re.compile(r'\b\(?\d{2}\)?\s?\d{4,5}-?\d{4}\b'),
        'cartao_credito': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'senha': re.compile(r'(senha|password|pwd|secret)["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE),
    }
    
    @classmethod
    def mask_cpf_cnpj(cls, value: str) -> str:
        """Mascara CPF/CNPJ: 123.456.789-00 -> 123.***.***-00"""
        if len(value) == 11:  # CPF
            return f"{value[:3]}.***.***-{value[-2:]}"
        elif len(value) == 14:  # CNPJ
            return f"{value[:2]}.***.***/{value[-7:]}"
        return value
    
    @classmethod
    def mask_email(cls, email: str) -> str:
        """Mascara email: user@example.com -> u***@example.com"""
        if '@' in email:
            local, domain = email.split('@', 1)
            if len(local) > 2:
                return f"{local[0]}***@{domain}"
            return f"***@{domain}"
        return email
    
    @classmethod
    def mask_telefone(cls, telefone: str) -> str:
        """Mascara telefone: (11) 99999-9999 -> (11) ****-9999"""
        # Manter DDD e últimos 4 dígitos
        digits = re.sub(r'\D', '', telefone)
        if len(digits) >= 6:
            return f"({digits[:2]}) ****-{digits[-4:]}"
        return "****"
    
    @classmethod
    def mask_cartao(cls, numero: str) -> str:
        """Mascara cartão: 1234 5678 9012 3456 -> **** **** **** 3456"""
        digits = re.sub(r'\D', '', numero)
        if len(digits) >= 4:
            return f"**** **** **** {digits[-4:]}"
        return "****"
    
    @classmethod
    def mask_string(cls, text: str) -> str:
        """
        Aplica masking em uma string
        
        Returns:
            String com PII mascarada
        """
        if not isinstance(text, str):
            return text
        
        masked = text
        
        # Mascara CPF/CNPJ
        def mask_cpf_match(match):
            return cls.mask_cpf_cnpj(match.group())
        masked = cls.PATTERNS['cpf'].sub(mask_cpf_match, masked)
        masked = cls.PATTERNS['cnpj'].sub(mask_cpf_match, masked)
        
        # Mascara emails
        def mask_email_match(match):
            return cls.mask_email(match.group())
        masked = cls.PATTERNS['email'].sub(mask_email_match, masked)
        
        # Mascara telefones
        def mask_tel_match(match):
            return cls.mask_telefone(match.group())
        masked = cls.PATTERNS['telefone'].sub(mask_tel_match, masked)
        
        # Mascara cartões
        def mask_card_match(match):
            return cls.mask_cartao(match.group())
        masked = cls.PATTERNS['cartao_credito'].sub(mask_card_match, masked)
        
        # Mascara senhas em JSON/logs
        def mask_password_match(match):
            return f"{match.group(1)}: '***'"
        masked = cls.PATTERNS['senha'].sub(mask_password_match, masked)
        
        return masked
    
    @classmethod
    def mask_dict(cls, data: Dict[str, Any], keys_to_mask: list = None) -> Dict[str, Any]:
        """
        Mascara PII em dicionário
        
        Args:
            data: Dicionário a mascarar
            keys_to_mask: Lista de chaves para mascarar (além da detecção automática)
        
        Returns:
            Dicionário com valores mascarados
        """
        if not isinstance(data, dict):
            return data
        
        # Chaves sensíveis padrão
        sensitive_keys = {
            'senha', 'password', 'pwd', 'secret', 'token', 
            'api_key', 'access_token', 'refresh_token',
            'cpf', 'cnpj', 'cartao', 'card_number'
        }
        
        if keys_to_mask:
            sensitive_keys.update(keys_to_mask)
        
        masked = {}
        for key, value in data.items():
            # Mascarar chaves sensíveis
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked[key] = '***'
            # Mascarar recursivamente dicionários aninhados
            elif isinstance(value, dict):
                masked[key] = cls.mask_dict(value, keys_to_mask)
            # Mascarar strings
            elif isinstance(value, str):
                masked[key] = cls.mask_string(value)
            # Manter outros tipos
            else:
                masked[key] = value
        
        return masked


class SafeLogger:
    """Logger que automaticamente mascara PII"""
    
    @staticmethod
    def info(message: str, *args, **kwargs):
        """Log info com masking"""
        masked_msg = PIIMasker.mask_string(str(message))
        current_app.logger.info(masked_msg, *args, **kwargs)
    
    @staticmethod
    def warning(message: str, *args, **kwargs):
        """Log warning com masking"""
        masked_msg = PIIMasker.mask_string(str(message))
        current_app.logger.warning(masked_msg, *args, **kwargs)
    
    @staticmethod
    def error(message: str, *args, **kwargs):
        """Log error com masking"""
        masked_msg = PIIMasker.mask_string(str(message))
        current_app.logger.error(masked_msg, *args, **kwargs)
    
    @staticmethod
    def debug(message: str, *args, **kwargs):
        """Log debug com masking"""
        masked_msg = PIIMasker.mask_string(str(message))
        current_app.logger.debug(masked_msg, *args, **kwargs)


__all__ = ['PIIMasker', 'SafeLogger']

