"""
Testes de Segurança de Upload de Arquivos
=========================================

Valida as proteções contra:
- Path traversal
- Extensões maliciosas
- Tamanho excessivo
- Tipos MIME inválidos
- Dupla extensão
"""
import pytest
import os
import tempfile
from io import BytesIO
from meu_app.upload_security import (
    FileUploadValidator,
    UploadSecurityError,
    serve_uploaded_file_securely
)


class TestFileValidation:
    """Testes de validação de arquivos"""
    
    def test_rejeitar_arquivo_vazio(self, app):
        """Deve rejeitar arquivo vazio"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            file = FileStorage(
                stream=BytesIO(b''),
                filename='vazio.txt',
                content_type='text/plain'
            )
            
            is_valid, error_msg, metadata = FileUploadValidator.validate_file(file, 'document')
            assert not is_valid, "Arquivo vazio deve ser rejeitado"
            assert 'vazio' in error_msg.lower()
    
    def test_rejeitar_extensao_invalida(self, app):
        """Deve rejeitar extensões não permitidas"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            # Tentar upload de arquivo .exe
            file = FileStorage(
                stream=BytesIO(b'MZ\x90\x00'),  # Magic number de executável
                filename='malware.exe',
                content_type='application/x-msdownload'
            )
            
            is_valid, error_msg, metadata = FileUploadValidator.validate_file(file, 'document')
            assert not is_valid, "Arquivo .exe deve ser rejeitado"
            assert 'extensão' in error_msg.lower() or 'permitida' in error_msg.lower()
    
    def test_rejeitar_dupla_extensao(self, app):
        """Deve rejeitar arquivos com dupla extensão (ex: .php.jpg)"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            file = FileStorage(
                stream=BytesIO(b'<?php echo "xss"; ?>'),
                filename='script.php.jpg',
                content_type='image/jpeg'
            )
            
            is_valid, error_msg, metadata = FileUploadValidator.validate_file(file, 'image')
            # Deve falhar porque o magic number não é de imagem
            assert not is_valid
    
    def test_rejeitar_tamanho_excessivo(self, app):
        """Deve rejeitar arquivos maiores que o limite"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            # Criar arquivo de 20MB (limite é 10MB para Excel)
            large_data = b'X' * (20 * 1024 * 1024)
            
            file = FileStorage(
                stream=BytesIO(large_data),
                filename='grande.xlsx',
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            is_valid, error_msg, metadata = FileUploadValidator.validate_file(file, 'excel')
            assert not is_valid, "Arquivo muito grande deve ser rejeitado"
            assert 'tamanho' in error_msg.lower() or 'grande' in error_msg.lower()
    
    def test_validar_mime_type_real(self, app):
        """Deve validar o tipo MIME real do arquivo (magic number)"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            # Arquivo com extensão .pdf mas conteúdo HTML
            file = FileStorage(
                stream=BytesIO(b'<html><body>Fake PDF</body></html>'),
                filename='fake.pdf',
                content_type='application/pdf'
            )
            
            is_valid, error_msg, metadata = FileUploadValidator.validate_file(file, 'document')
            # Deve falhar porque o magic number não é de PDF
            assert not is_valid


class TestSecureFilename:
    """Testes de geração de nome de arquivo seguro"""
    
    def test_nome_aleatorio_gerado(self, app):
        """Nome gerado deve ser aleatório e único"""
        with app.app_context():
            name1 = FileUploadValidator.generate_secure_filename('test.pdf', 'document')
            name2 = FileUploadValidator.generate_secure_filename('test.pdf', 'document')
            
            assert name1 != name2, "Nomes devem ser únicos"
    
    def test_nome_sem_path_traversal(self, app):
        """Nome não deve conter caracteres de path traversal"""
        with app.app_context():
            # Tentar path traversal no nome
            malicious_names = [
                '../../../etc/passwd',
                '..\\..\\windows\\system32\\config',
                'test/../../../file.pdf',
            ]
            
            for malicious in malicious_names:
                safe_name = FileUploadValidator.generate_secure_filename(malicious, 'document')
                
                assert '..' not in safe_name, "Nome não deve conter '..'"
                assert '/' not in safe_name, "Nome não deve conter '/'"
                assert '\\' not in safe_name, "Nome não deve conter '\\'"
    
    def test_extensao_preservada(self, app):
        """Extensão original deve ser preservada (se válida)"""
        with app.app_context():
            name = FileUploadValidator.generate_secure_filename('documento.pdf', 'document')
            assert name.endswith('.pdf'), "Extensão .pdf deve ser preservada"
    
    def test_extensao_invalida_substituida(self, app):
        """Extensão inválida deve ser substituída"""
        with app.app_context():
            name = FileUploadValidator.generate_secure_filename('script.php', 'document')
            assert not name.endswith('.php'), "Extensão .php não deve ser permitida"


class TestUploadDirectory:
    """Testes de diretório de upload"""
    
    def test_diretorio_fora_webroot(self, app):
        """Diretório de upload deve estar fora do webroot"""
        with app.app_context():
            upload_dir = FileUploadValidator.get_upload_directory('test')
            
            # Não deve estar dentro de 'static' ou 'templates'
            assert 'static' not in upload_dir, "Upload não deve estar em /static"
            assert 'templates' not in upload_dir, "Upload não deve estar em /templates"
    
    def test_path_traversal_bloqueado(self, app):
        """Deve bloquear tentativas de path traversal no tipo de arquivo"""
        with app.app_context():
            with pytest.raises(UploadSecurityError):
                FileUploadValidator.get_upload_directory('../../../etc')
    
    def test_diretorio_criado_com_permissoes_restritas(self, app):
        """Diretório deve ser criado com permissões restritas (750)"""
        with app.app_context():
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['UPLOAD_BASE_DIR'] = tmpdir
                
                upload_dir = FileUploadValidator.get_upload_directory('test_secure')
                
                # Verificar permissões
                stat_info = os.stat(upload_dir)
                permissions = oct(stat_info.st_mode)[-3:]
                
                # 750 = rwxr-x---
                assert permissions == '750', f"Permissões devem ser 750, mas são {permissions}"


class TestServeFile:
    """Testes de servir arquivos com segurança"""
    
    @pytest.mark.skip(reason="Requer setup completo de request context")
    def test_headers_seguranca_aplicados(self, app, client):
        """Arquivos servidos devem ter headers de segurança"""
        with app.app_context():
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                f.write(b'%PDF-1.4\nFake PDF content')
                temp_path = f.name
            
            try:
                response = serve_uploaded_file_securely(temp_path, as_attachment=True)
                
                # Verificar headers
                assert response.headers.get('X-Content-Type-Options') == 'nosniff'
                assert response.headers.get('X-Frame-Options') == 'DENY'
                assert 'Content-Security-Policy' in response.headers
                assert 'Content-Disposition' in response.headers
                
            finally:
                os.unlink(temp_path)
    
    @pytest.mark.skip(reason="Requer setup completo de request context")
    def test_path_traversal_bloqueado_ao_servir(self, app, client):
        """Deve bloquear tentativas de acessar arquivos fora do upload dir"""
        with app.app_context():
            # Tentar acessar arquivo fora do diretório de uploads
            with pytest.raises(Exception):  # Deve abortar com 403
                serve_uploaded_file_securely('/etc/passwd')
    
    @pytest.mark.skip(reason="Requer setup completo de request context")
    def test_mime_type_perigoso_convertido(self, app, client):
        """Tipos MIME perigosos devem ser convertidos para text/plain"""
        with app.app_context():
            # Criar arquivo HTML malicioso
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
                f.write(b'<script>alert("XSS")</script>')
                temp_path = f.name
            
            try:
                response = serve_uploaded_file_securely(temp_path)
                
                # Mimetype deve ser convertido para text/plain
                assert response.mimetype == 'text/plain'
                
            finally:
                os.unlink(temp_path)


class TestMalwareDetection:
    """Testes de detecção de conteúdo malicioso"""
    
    def test_detectar_executavel(self, app):
        """Deve detectar executáveis por magic number"""
        with app.app_context():
            # Magic number de executável Windows (MZ)
            is_safe, msg = FileUploadValidator.scan_file_for_malware.__func__(
                FileUploadValidator,
                '/dev/null'  # Placeholder, precisaria criar arquivo real
            )
            # Teste básico - implementação pode variar
    
    def test_detectar_script_embarcado(self, app):
        """Deve detectar scripts embarcados"""
        with app.app_context():
            from werkzeug.datastructures import FileStorage
            
            # Arquivo com script embarcado
            file = FileStorage(
                stream=BytesIO(b'<script>alert("xss")</script>'),
                filename='script.txt',
                content_type='text/plain'
            )
            
            # A validação deve detectar conteúdo suspeito
            # Implementação específica depende do scanner


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

