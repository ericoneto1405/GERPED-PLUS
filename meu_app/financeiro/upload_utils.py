"""
Utilitários para validação e processamento seguro de uploads
Fase 7 - Upload Seguro com validação robusta
"""

import hashlib
import os
import secrets
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
import magic
from ..time_utils import now_utc


# Tipos MIME permitidos para uploads de comprovantes
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'application/pdf',
}

# Extensões permitidas
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}

# Tamanho máximo por arquivo (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024


class UploadValidationError(Exception):
    """Erro de validação de upload"""
    pass


def generate_secure_filename(original_filename: str) -> str:
    """
    Gera nome de arquivo seguro com hash
    
    Args:
        original_filename: Nome original do arquivo
    
    Returns:
        Nome seguro: hash_random.ext
    """
    # Extrair extensão segura
    _, ext = os.path.splitext(secure_filename(original_filename))
    ext = ext.lower()
    
    # Gerar hash aleatório (16 bytes = 32 chars hex)
    random_hash = secrets.token_hex(16)
    
    # Timestamp para evitar colisões
    timestamp = int(now_utc().timestamp())
    
    return f"{random_hash}_{timestamp}{ext}"


def calculate_file_hash(file_path: str) -> str:
    """
    Calcula SHA-256 do arquivo
    
    Args:
        file_path: Caminho do arquivo
    
    Returns:
        Hash SHA-256 em hexadecimal
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Ler em chunks para não sobrecarregar memória
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def validate_file_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Valida extensão do arquivo
    
    Args:
        filename: Nome do arquivo
    
    Returns:
        (válido, mensagem_erro)
    """
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão não permitida: {ext}. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, None


def validate_file_mime(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Valida tipo MIME real do arquivo (não apenas extensão)
    
    Args:
        file_path: Caminho do arquivo
    
    Returns:
        (válido, mensagem_erro)
    """
    try:
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(file_path)
        
        if file_mime not in ALLOWED_MIME_TYPES:
            return False, f"Tipo de arquivo não permitido: {file_mime}. Permitidos: {', '.join(ALLOWED_MIME_TYPES)}"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro ao validar tipo de arquivo: {str(e)}"


def validate_file_size(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Valida tamanho do arquivo
    
    Args:
        file_path: Caminho do arquivo
    
    Returns:
        (válido, mensagem_erro)
    """
    try:
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            return False, f"Arquivo muito grande: {size_mb:.1f}MB. Máximo: {max_mb}MB"
        
        if file_size == 0:
            return False, "Arquivo vazio"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro ao validar tamanho: {str(e)}"


def validate_upload(file_path: str, original_filename: str) -> None:
    """
    Valida upload completo (extensão + MIME + tamanho)
    
    Args:
        file_path: Caminho do arquivo salvo
        original_filename: Nome original do arquivo
    
    Raises:
        UploadValidationError: Se validação falhar
    """
    # 1. Validar extensão
    valid, error = validate_file_extension(original_filename)
    if not valid:
        raise UploadValidationError(error)
    
    # 2. Validar tipo MIME real
    valid, error = validate_file_mime(file_path)
    if not valid:
        raise UploadValidationError(error)
    
    # 3. Validar tamanho
    valid, error = validate_file_size(file_path)
    if not valid:
        raise UploadValidationError(error)


def save_upload_securely(file, upload_dir: str) -> Tuple[str, str, str]:
    """
    Salva arquivo de forma segura com validação completa
    
    Args:
        file: FileStorage do Flask
        upload_dir: Diretório de destino
    
    Returns:
        (caminho_arquivo, nome_seguro, hash_sha256)
    
    Raises:
        UploadValidationError: Se validação falhar
    """
    from datetime import datetime
    
    # 1. Gerar nome seguro
    secure_name = generate_secure_filename(file.filename)
    
    # 2. Criar diretório se não existir
    os.makedirs(upload_dir, exist_ok=True)
    
    # 3. Caminho completo
    file_path = os.path.join(upload_dir, secure_name)
    
    # 4. Salvar arquivo
    file.save(file_path)
    
    try:
        # 5. Validar arquivo salvo
        validate_upload(file_path, file.filename)
        
        # 6. Calcular hash
        file_hash = calculate_file_hash(file_path)
        
        return file_path, secure_name, file_hash
        
    except UploadValidationError:
        # Se validação falhar, remover arquivo
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
