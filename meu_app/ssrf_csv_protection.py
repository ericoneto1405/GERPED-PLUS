"""
Proteção contra SSRF e CSV Injection
====================================

SSRF (Server-Side Request Forgery): Validação de URLs
CSV Injection: Escape de fórmulas em exportações
"""
import re
import ipaddress
from typing import Tuple
from urllib.parse import urlparse
from flask import current_app


class SSRFProtection:
    """Proteção contra Server-Side Request Forgery"""
    
    # IPs e redes privadas (RFC1918)
    PRIVATE_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),  # localhost
        ipaddress.ip_network('169.254.0.0/16'),  # link-local
        ipaddress.ip_network('::1/128'),  # IPv6 localhost
        ipaddress.ip_network('fe80::/10'),  # IPv6 link-local
    ]
    
    # Domínios perigosos (AWS metadata, etc)
    DANGEROUS_DOMAINS = [
        '169.254.169.254',  # AWS metadata
        'metadata.google.internal',  # GCP metadata
        'metadata',
        'localhost',
        '0.0.0.0',
    ]
    
    @classmethod
    def is_safe_url(cls, url: str) -> Tuple[bool, str]:
        """
        Valida se URL é segura (não é SSRF)
        
        Returns:
            (is_safe, error_message)
        """
        try:
            if not url:
                return False, "URL vazia"
            
            # Parse URL
            parsed = urlparse(url)
            
            # Validar scheme (apenas http/https)
            if parsed.scheme not in ('http', 'https'):
                return False, f"Scheme não permitido: {parsed.scheme}"
            
            # Validar hostname
            hostname = parsed.hostname
            if not hostname:
                return False, "Hostname inválido"
            
            # Verificar domínios perigosos
            if any(dangerous in hostname.lower() for dangerous in cls.DANGEROUS_DOMAINS):
                current_app.logger.warning(f"[SSRF] Tentativa de acesso a domínio perigoso: {hostname}")
                return False, "Domínio não permitido"
            
            # Resolver IP e verificar se é privado
            try:
                import socket
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
                
                # Verificar se IP está em rede privada
                for network in cls.PRIVATE_NETWORKS:
                    if ip in network:
                        current_app.logger.warning(f"[SSRF] Tentativa de acesso a IP privado: {ip}")
                        return False, "Acesso a redes privadas não permitido"
                
            except (socket.gaierror, ValueError) as e:
                current_app.logger.warning(f"[SSRF] Erro ao resolver hostname: {hostname} - {e}")
                return False, "Erro ao resolver hostname"
            
            return True, ""
            
        except Exception as e:
            current_app.logger.error(f"Erro em is_safe_url: {e}")
            return False, str(e)
    
    @classmethod
    def validate_and_fetch(cls, url: str, timeout: int = 5) -> Tuple[bool, str, bytes]:
        """
        Valida URL e faz requisição segura
        
        Args:
            url: URL a ser acessada
            timeout: Timeout em segundos
            
        Returns:
            (success, error_message, content)
        """
        import requests
        
        # Validar URL
        is_safe, error = cls.is_safe_url(url)
        if not is_safe:
            return False, error, b''
        
        try:
            # Fazer requisição com timeout
            response = requests.get(
                url,
                timeout=timeout,
                allow_redirects=False,  # Não seguir redirects (pode ser SSRF)
                verify=True,  # Verificar certificados SSL
            )
            
            response.raise_for_status()
            
            return True, "", response.content
            
        except requests.exceptions.Timeout:
            return False, "Timeout ao acessar URL", b''
        except requests.exceptions.SSLError:
            return False, "Erro de certificado SSL", b''
        except requests.exceptions.RequestException as e:
            return False, f"Erro ao acessar URL: {str(e)}", b''


class CSVInjectionProtection:
    """Proteção contra CSV Injection (Formula Injection)"""
    
    # Caracteres perigosos em início de célula
    DANGEROUS_PREFIXES = ['=', '+', '-', '@', '\t', '\r']
    
    @classmethod
    def escape_cell(cls, value: str) -> str:
        """
        Escapa célula CSV para prevenir injection
        
        Args:
            value: Valor da célula
            
        Returns:
            Valor escapado
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Verificar se começa com caractere perigoso
        if value and value[0] in cls.DANGEROUS_PREFIXES:
            # Adicionar apóstrofo no início para forçar como texto
            value = "'" + value
            current_app.logger.warning(f"[CSV Injection] Célula escapada: {value[:50]}")
        
        return value
    
    @classmethod
    def escape_row(cls, row: list) -> list:
        """
        Escapa todas as células de uma linha
        
        Args:
            row: Lista com valores da linha
            
        Returns:
            Lista com valores escapados
        """
        return [cls.escape_cell(cell) for cell in row]
    
    @classmethod
    def escape_dataframe(cls, df):
        """
        Escapa todas as células de um DataFrame pandas
        
        Args:
            df: DataFrame pandas
            
        Returns:
            DataFrame escapado
        """
        import pandas as pd
        
        # Aplicar escape em todas as colunas
        for col in df.columns:
            if df[col].dtype == 'object':  # Apenas colunas de string
                df[col] = df[col].apply(cls.escape_cell)
        
        return df


def safe_export_csv(data: list, filename: str = 'export.csv') -> bytes:
    """
    Exporta dados para CSV de forma segura (com escape)
    
    Args:
        data: Lista de dicionários ou lista de listas
        filename: Nome do arquivo
        
    Returns:
        Bytes do arquivo CSV
    """
    import csv
    import io
    
    output = io.StringIO()
    
    if not data:
        return b''
    
    # Se for lista de dicts, pegar headers
    if isinstance(data[0], dict):
        headers = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        # Escrever dados com escape
        for row in data:
            escaped_row = {k: CSVInjectionProtection.escape_cell(v) for k, v in row.items()}
            writer.writerow(escaped_row)
    
    # Se for lista de listas
    else:
        writer = csv.writer(output)
        
        # Escrever dados com escape
        for row in data:
            escaped_row = CSVInjectionProtection.escape_row(row)
            writer.writerow(escaped_row)
    
    # Retornar bytes
    return output.getvalue().encode('utf-8')


__all__ = [
    'SSRFProtection',
    'CSVInjectionProtection',
    'safe_export_csv',
]

