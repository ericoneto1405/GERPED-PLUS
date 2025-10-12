"""
Módulo de Segurança para Upload de Arquivos
==========================================

Este módulo contém funções para validação e processamento seguro
de arquivos enviados pelos usuários.

Autor: Sistema de Gestão Empresarial
Data: 2024
"""

import os
import uuid
import magic
from werkzeug.utils import secure_filename
from flask import current_app
from typing import Tuple, Optional
import mimetypes


class UploadSecurityError(Exception):
    """Exceção personalizada para erros de segurança no upload"""
    pass


class FileUploadValidator:
    """Classe para validação segura de upload de arquivos"""
    
    # Tipos MIME permitidos para diferentes tipos de arquivo
    ALLOWED_MIME_TYPES = {
        'excel': [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',  # .xls
            'application/vnd.oasis.opendocument.spreadsheet',  # .ods
            'application/zip'  # .xlsx são arquivos ZIP comprimidos
            # application/octet-stream é tratado com validação especial de assinatura
        ],
        'csv': [
            'text/csv',
            'application/csv',
            'text/plain'
        ],
        'image': [
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/heic',
            'image/heif'
        ],
        'document': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    }
    
    # Extensões permitidas (como backup)
    ALLOWED_EXTENSIONS = {
        'excel': {'.xlsx', '.xls', '.ods'},
        'csv': {'.csv', '.txt'},
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'},
        'document': {'.pdf', '.doc', '.docx'}
    }
    
    # Tamanho máximo por tipo de arquivo (em bytes)
    MAX_FILE_SIZES = {
        'excel': 10 * 1024 * 1024,  # 10MB
        'csv': 5 * 1024 * 1024,     # 5MB
        'image': 5 * 1024 * 1024,   # 5MB
        'document': 10 * 1024 * 1024 # 10MB
    }
    
    @classmethod
    def validate_file(cls, file, file_type: str) -> Tuple[bool, str, Optional[dict]]:
        """
        Valida um arquivo enviado
        
        Args:
            file: Objeto de arquivo do Flask
            file_type: Tipo de arquivo esperado ('excel', 'csv', 'image', 'document')
            
        Returns:
            Tuple[bool, str, dict]: (é_válido, mensagem_erro, metadados_arquivo)
        """
        try:
            if not file or not file.filename:
                return False, "Nenhum arquivo foi enviado", None
            
            # Verificar se o tipo de arquivo é suportado
            if file_type not in cls.ALLOWED_MIME_TYPES:
                return False, f"Tipo de arquivo '{file_type}' não é suportado", None
            
            # Obter informações do arquivo
            filename = secure_filename(file.filename)
            file_size = len(file.read())
            file.seek(0)  # Voltar ao início do arquivo
            
            # Verificar tamanho do arquivo
            max_size = cls.MAX_FILE_SIZES.get(file_type, 5 * 1024 * 1024)
            if file_size > max_size:
                return False, f"Arquivo muito grande. Tamanho máximo: {max_size // (1024*1024)}MB", None
            
            # Verificar extensão do arquivo
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in cls.ALLOWED_EXTENSIONS[file_type]:
                return False, f"Extensão de arquivo não permitida. Permitidas: {', '.join(cls.ALLOWED_EXTENSIONS[file_type])}", None
            
            # Verificar tipo MIME real do arquivo
            file_mime = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)  # Voltar ao início do arquivo
            
            # Validação especial para arquivos Excel com MIME genérico
            if file_type == 'excel' and file_mime == 'application/octet-stream':
                # Verificar se é realmente um arquivo Excel lendo a assinatura
                file_header = file.read(8)
                file.seek(0)
                
                # Assinaturas de arquivo Excel/ZIP (xlsx é um arquivo ZIP)
                # PK\x03\x04 = ZIP (usado por .xlsx)
                # \xd0\xcf\x11\xe0 = OLE2 (usado por .xls antigo)
                is_valid_excel = (
                    file_header.startswith(b'PK\x03\x04') or  # .xlsx (ZIP)
                    file_header.startswith(b'\xd0\xcf\x11\xe0')  # .xls (OLE2)
                )
                
                if not is_valid_excel:
                    return False, f"Arquivo não é um Excel válido. Tipo detectado: {file_mime}", None
                
                current_app.logger.info(f"Arquivo Excel validado por assinatura (MIME genérico)")
            
            elif file_mime not in cls.ALLOWED_MIME_TYPES[file_type]:
                return False, f"Tipo de arquivo não permitido. Tipo detectado: {file_mime}", None
            
            # Verificar se o arquivo não está vazio
            if file_size == 0:
                return False, "Arquivo está vazio", None
            
            # Metadados do arquivo
            metadata = {
                'original_filename': file.filename,
                'secure_filename': filename,
                'file_size': file_size,
                'mime_type': file_mime,
                'extension': file_ext
            }
            
            return True, "Arquivo válido", metadata
            
        except Exception as e:
            current_app.logger.error(f"Erro na validação do arquivo: {str(e)}")
            return False, f"Erro na validação do arquivo: {str(e)}", None
    
    @classmethod
    def generate_secure_filename(cls, original_filename: str, file_type: str) -> str:
        """
        Gera um nome de arquivo seguro, único e aleatório (anti path-traversal)
        
        Args:
            original_filename: Nome original do arquivo
            file_type: Tipo do arquivo
            
        Returns:
            str: Nome de arquivo seguro e único
        """
        # Obter extensão do arquivo original (sanitizada)
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # Validar extensão (previne dupla extensão como .php.jpg)
        allowed_exts = cls.ALLOWED_EXTENSIONS.get(file_type, set())
        if file_ext not in allowed_exts:
            file_ext = '.bin'  # Extensão segura padrão
        
        # Gerar nome completamente aleatório (UUID4)
        unique_id = str(uuid.uuid4())
        
        # Adicionar timestamp para evitar colisões
        import time
        timestamp = int(time.time())
        
        # Nome final: tipo_timestamp_uuid.ext
        secure_name = f"{file_type}_{timestamp}_{unique_id}{file_ext}"
        
        # Garantir que não contém caracteres perigosos (path traversal)
        secure_name = secure_name.replace('..', '').replace('/', '').replace('\\', '')
        
        return secure_name
    
    @classmethod
    def get_upload_directory(cls, file_type: str) -> str:
        """
        Obtém o diretório de upload FORA DO WEBROOT
        
        Args:
            file_type: Tipo do arquivo
            
        Returns:
            str: Caminho absoluto do diretório de upload
        """
        # Base de uploads configurável (FORA do webroot em produção)
        base_upload_dir = os.getenv('UPLOAD_BASE_DIR', 
                                     os.path.join(current_app.root_path, '..', 'uploads'))
        
        # Garantir caminho absoluto
        base_upload_dir = os.path.abspath(base_upload_dir)
        
        # Validar file_type (prevenir path traversal)
        safe_file_type = file_type.replace('..', '').replace('/', '').replace('\\', '')
        
        # Diretório específico para o tipo de arquivo
        type_dir = os.path.join(base_upload_dir, safe_file_type)
        
        # Verificar se está dentro do base_upload_dir (anti path-traversal)
        type_dir_abs = os.path.abspath(type_dir)
        if not type_dir_abs.startswith(base_upload_dir):
            raise UploadSecurityError("Tentativa de path traversal detectada")
        
        # Criar diretório com permissões restritas
        os.makedirs(type_dir, mode=0o750, exist_ok=True)
        
        return type_dir
    
    @classmethod
    def save_file(cls, file, file_type: str) -> Tuple[bool, str, Optional[str]]:
        """
        Salva um arquivo de forma segura
        
        Args:
            file: Objeto de arquivo do Flask
            file_type: Tipo do arquivo
            
        Returns:
            Tuple[bool, str, str]: (sucesso, mensagem, caminho_arquivo)
        """
        try:
            # Validar arquivo primeiro
            is_valid, error_msg, metadata = cls.validate_file(file, file_type)
            if not is_valid:
                return False, error_msg, None
            
            # Gerar nome de arquivo seguro
            secure_filename = cls.generate_secure_filename(
                metadata['original_filename'], 
                file_type
            )
            
            # Obter diretório de upload
            upload_dir = cls.get_upload_directory(file_type)
            
            # Caminho completo do arquivo
            file_path = os.path.join(upload_dir, secure_filename)
            
            # Salvar arquivo
            file.save(file_path)
            
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(file_path):
                return False, "Erro ao salvar arquivo", None
            
            # Verificar tamanho do arquivo salvo
            saved_size = os.path.getsize(file_path)
            if saved_size != metadata['file_size']:
                # Remover arquivo corrompido
                os.remove(file_path)
                return False, "Arquivo corrompido durante o salvamento", None
            
            current_app.logger.info(f"Arquivo salvo com sucesso: {file_path}")
            return True, "Arquivo salvo com sucesso", file_path
            
        except Exception as e:
            current_app.logger.error(f"Erro ao salvar arquivo: {str(e)}")
            return False, f"Erro ao salvar arquivo: {str(e)}", None
    
    @classmethod
    def cleanup_file(cls, file_path: str) -> bool:
        """
        Remove um arquivo de forma segura
        
        Args:
            file_path: Caminho do arquivo a ser removido
            
        Returns:
            bool: True se removido com sucesso
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"Arquivo removido: {file_path}")
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Erro ao remover arquivo: {str(e)}")
            return False
    
    @classmethod
    def scan_file_for_malware(cls, file_path: str) -> Tuple[bool, str]:
        """
        Escaneia arquivo em busca de conteúdo malicioso (implementação básica)
        
        Args:
            file_path: Caminho do arquivo a ser escaneado
            
        Returns:
            Tuple[bool, str]: (é_seguro, mensagem)
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Ler apenas os primeiros 1KB
            
            # Verificar por assinaturas de arquivos executáveis
            executable_signatures = [
                b'MZ',  # PE executável
                b'\x7fELF',  # ELF executável
                b'\xfe\xed\xfa',  # Mach-O executável
                b'#!/',  # Script shell
                b'<script',  # JavaScript
                b'<iframe',  # HTML malicioso
                b'<object',  # Objeto HTML
                b'<embed'   # Embed HTML
            ]
            
            for signature in executable_signatures:
                if signature in content:
                    return False, f"Arquivo contém conteúdo potencialmente malicioso: {signature}"
            
            # Verificar por macros do Office (básico)
            if b'VBA' in content or b'Macro' in content:
                return False, "Arquivo contém macros que podem ser maliciosas"
            
            return True, "Arquivo parece seguro"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao escanear arquivo: {str(e)}")
            return False, f"Erro ao escanear arquivo: {str(e)}"


def validate_excel_upload(file) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e salva upload de arquivo Excel de forma segura
    
    Args:
        file: Objeto de arquivo do Flask
        
    Returns:
        Tuple[bool, str, str]: (sucesso, mensagem, caminho_arquivo)
    """
    return FileUploadValidator.save_file(file, 'excel')


def validate_csv_upload(file) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e salva upload de arquivo CSV de forma segura
    
    Args:
        file: Objeto de arquivo do Flask
        
    Returns:
        Tuple[bool, str, str]: (sucesso, mensagem, caminho_arquivo)
    """
    return FileUploadValidator.save_file(file, 'csv')


def validate_image_upload(file) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e salva upload de arquivo de imagem de forma segura
    
    Args:
        file: Objeto de arquivo do Flask
        
    Returns:
        Tuple[bool, str, str]: (sucesso, mensagem, caminho_arquivo)
    """
    return FileUploadValidator.save_file(file, 'image')


def validate_document_upload(file) -> Tuple[bool, str, Optional[str]]:
    """
    Valida e salva upload de arquivo de documento de forma segura
    
    Args:
        file: Objeto de arquivo do Flask
        
    Returns:
        Tuple[bool, str, str]: (sucesso, mensagem, caminho_arquivo)
    """
    return FileUploadValidator.save_file(file, 'document')


def serve_uploaded_file_securely(file_path: str, as_attachment: bool = True, download_name: str = None):
    """
    Serve arquivo de upload com headers de segurança apropriados
    
    Args:
        file_path: Caminho absoluto do arquivo
        as_attachment: Se True, força download; se False, tenta exibir inline
        download_name: Nome do arquivo no download (se None, usa nome original)
        
    Returns:
        Flask Response com arquivo e headers de segurança
    """
    from flask import send_file, abort
    import mimetypes
    
    # Verificar se arquivo existe
    if not os.path.exists(file_path):
        current_app.logger.error(f"Arquivo não encontrado: {file_path}")
        abort(404, "Arquivo não encontrado")
    
    # Verificar se está dentro do diretório de uploads (anti path-traversal)
    base_upload_dir = os.getenv('UPLOAD_BASE_DIR', 
                                 os.path.join(current_app.root_path, '..', 'uploads'))
    base_upload_dir = os.path.abspath(base_upload_dir)
    file_path_abs = os.path.abspath(file_path)
    
    if not file_path_abs.startswith(base_upload_dir):
        current_app.logger.error(f"Tentativa de acesso fora do upload dir: {file_path}")
        abort(403, "Acesso negado")
    
    # Determinar mimetype seguro
    mimetype, _ = mimetypes.guess_type(file_path)
    if not mimetype:
        mimetype = 'application/octet-stream'
    
    # Forçar tipos seguros para evitar execução de código
    dangerous_mimetypes = {
        'text/html': 'text/plain',
        'application/javascript': 'text/plain',
        'application/x-javascript': 'text/plain',
        'text/javascript': 'text/plain',
    }
    
    if mimetype in dangerous_mimetypes:
        current_app.logger.warning(f"Mimetype perigoso convertido: {mimetype} -> text/plain")
        mimetype = dangerous_mimetypes[mimetype]
    
    # Nome do arquivo para download
    if download_name is None:
        download_name = os.path.basename(file_path)
    
    try:
        response = send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=as_attachment,
            download_name=download_name
        )
        
        # Headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'none'"
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Se attachment, adicionar Content-Disposition explícito
        if as_attachment:
            response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
        
        current_app.logger.info(f"Arquivo servido com segurança: {file_path}")
        return response
        
    except Exception as e:
        current_app.logger.error(f"Erro ao servir arquivo: {str(e)}")
        abort(500, "Erro ao servir arquivo")
