"""
Serviços para o módulo de usuários
Contém toda a lógica de negócio separada das rotas
"""
from ..models import db, Usuario, LogAtividade
from flask import current_app, session
from typing import Dict, List, Tuple, Optional
import json
from .repositories import UsuarioRepository

class UsuarioService:
    """Serviço para operações relacionadas a usuários"""
    
    def __init__(self):
        """Inicializa o serviço com seu repository"""
        self.repository = UsuarioRepository()
    
    def criar_usuario(self, nome: str, senha: str, tipo: str, acessos: Dict[str, bool]) -> Tuple[bool, str, Optional[Usuario]]:
        """
        Cria um novo usuário
        
        Args:
            nome: Nome do usuário
            senha: Senha do usuário
            tipo: Tipo do usuário (admin ou comum)
            acessos: Dicionário com os acessos permitidos
            
        Returns:
            Tuple[bool, str, Optional[Usuario]]: (sucesso, mensagem, usuario)
        """
        try:
            # Validações
            if not nome or not nome.strip():
                return False, "Nome do usuário é obrigatório", None
            
            if not senha or not senha.strip():
                return False, "Senha é obrigatória", None
            valido, mensagem = self.validar_politica_senha(senha.strip())
            if not valido:
                return False, mensagem, None
            
            if tipo not in ['admin', 'comum']:
                return False, "Tipo de usuário inválido", None
            
            # Verificar se já existe usuário com mesmo nome (usando repository)
            if self.repository.verificar_nome_existe(nome.strip()):
                return False, f"Já existe um usuário com o nome '{nome}'", None
            
            # Criar usuário
            novo_usuario = Usuario(
                nome=nome.strip(),
                senha_hash='',  # Será definido pelo método set_senha
                tipo=tipo,
                acesso_clientes=acessos.get('acesso_clientes', False),
                acesso_produtos=acessos.get('acesso_produtos', False),
                acesso_pedidos=acessos.get('acesso_pedidos', False),
                acesso_financeiro=acessos.get('acesso_financeiro', False),
                acesso_logistica=acessos.get('acesso_logistica', False)
            )
            
            # Definir senha usando hash seguro
            novo_usuario.set_senha(senha.strip())
            
            # Usar repository para criar
            novo_usuario = self.repository.criar(novo_usuario)
            
            # Registrar atividade
            self._registrar_atividade(
                tipo_atividade="Criação de Usuário",
                titulo="Usuário Criado",
                descricao=f"Usuário: {nome} - Tipo: {tipo}",
                modulo="Usuários",
                dados_extras={"usuario_id": novo_usuario.id, "nome": nome, "tipo": tipo}
            )
            
            current_app.logger.info(f"Usuário criado: {novo_usuario.nome} (ID: {novo_usuario.id})")
            
            return True, "Usuário criado com sucesso", novo_usuario
            
        except Exception as e:
            current_app.logger.error(f"Erro ao criar usuário: {str(e)}")
            return False, f"Erro ao criar usuário: {str(e)}", None
    
    def excluir_usuario(self, usuario_id: int) -> Tuple[bool, str]:
        """
        Exclui um usuário
        
        Args:
            usuario_id: ID do usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Buscar usuário usando repository
            usuario = self.repository.buscar_por_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # Verificar se não é o último admin
            if usuario.tipo == 'admin':
                admins = self.repository.listar_por_tipo('admin')
                if len(admins) <= 1:
                    return False, "Não é possível excluir o último administrador do sistema"
            
            nome_usuario = usuario.nome
            
            # Usar repository para excluir
            self.repository.excluir(usuario)
            
            # Registrar atividade
            self._registrar_atividade(
                tipo_atividade="Exclusão de Usuário",
                titulo="Usuário Excluído",
                descricao=f"Usuário excluído: {nome_usuario}",
                modulo="Usuários",
                dados_extras={"usuario_id": usuario_id, "nome": nome_usuario}
            )
            
            current_app.logger.info(f"Usuário excluído: {nome_usuario} (ID: {usuario_id})")
            
            return True, "Usuário excluído com sucesso"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao excluir usuário: {str(e)}")
            return False, f"Erro ao excluir usuário: {str(e)}"
    
    def listar_usuarios(self) -> List[Usuario]:
        """
        Lista todos os usuários
        
        Returns:
            List[Usuario]: Lista de usuários
        """
        try:
            return self.repository.listar_todos()
        except Exception as e:
            current_app.logger.error(f"Erro ao listar usuários: {str(e)}")
            return []
    
    def buscar_usuario(self, usuario_id: int) -> Optional[Usuario]:
        """
        Busca um usuário por ID
        
        Args:
            usuario_id: ID do usuário
            
        Returns:
            Optional[Usuario]: Usuário encontrado ou None
        """
        try:
            return self.repository.buscar_por_id(usuario_id)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar usuário: {str(e)}")
            return None
    
    def verificar_acesso_admin(self, usuario_tipo: str) -> bool:
        """
        Verifica se o usuário tem acesso de administrador
        
        Args:
            usuario_tipo: Tipo do usuário
            
        Returns:
            bool: True se tem acesso de admin
        """
        return usuario_tipo == 'admin'
    
    def alterar_senha_usuario(self, usuario_id: int, senha_atual: str, nova_senha: str, confirmar_senha: str) -> Tuple[bool, str]:
        """
        Altera a senha de um usuário
        
        Args:
            usuario_id: ID do usuário
            senha_atual: Senha atual do usuário
            nova_senha: Nova senha
            confirmar_senha: Confirmação da nova senha
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Validações
            if not nova_senha or not nova_senha.strip():
                return False, "Nova senha é obrigatória"
            
            if not confirmar_senha or not confirmar_senha.strip():
                return False, "Confirmação de senha é obrigatória"
            
            if nova_senha != confirmar_senha:
                return False, "Nova senha e confirmação não coincidem"
            
            # Validar política de senha
            validacao, mensagem = self.validar_politica_senha(nova_senha)
            if not validacao:
                return False, mensagem
            
            # Buscar usuário usando repository
            usuario = self.repository.buscar_por_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # Verificar senha atual
            if not usuario.check_senha(senha_atual):
                return False, "Senha atual incorreta"
            
            # Alterar senha
            usuario.set_senha(nova_senha.strip())
            
            # Usar repository para atualizar
            self.repository.atualizar(usuario)
            
            # Registrar atividade
            self._registrar_atividade(
                tipo_atividade="Alteração de Senha",
                titulo="Senha Alterada",
                descricao=f"Usuário: {usuario.nome} - Senha alterada com sucesso",
                modulo="Usuários",
                dados_extras={"usuario_id": usuario_id, "nome": usuario.nome}
            )
            
            current_app.logger.info(f"Senha alterada para usuário {usuario.nome} (ID: {usuario_id})")
            return True, "Senha alterada com sucesso"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao alterar senha: {str(e)}")
            return False, f"Erro ao alterar senha: {str(e)}"
    
    def validar_politica_senha(self, senha: str) -> Tuple[bool, str]:
        """
        Valida se a senha atende aos critérios de segurança
        
        Args:
            senha: Senha a ser validada
            
        Returns:
            Tuple[bool, str]: (valida, mensagem)
        """
        if len(senha) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        
        if len(senha) > 50:
            return False, "Senha deve ter no máximo 50 caracteres"
        
        # Verificar se tem pelo menos um número
        if not any(char.isdigit() for char in senha):
            return False, "Senha deve conter pelo menos um número"
        
        # Verificar se tem pelo menos uma letra
        if not any(char.isalpha() for char in senha):
            return False, "Senha deve conter pelo menos uma letra"
        
        # Verificar senhas comuns
        senhas_fracas = ['123456', 'password', 'admin', '123456789', 'qwerty', 'abc123']
        if senha.lower() in senhas_fracas:
            return False, "Esta senha é muito comum. Escolha uma senha mais segura"
        
        return True, "Senha válida"
    
    def editar_usuario(self, usuario_id: int, nome: str, tipo: str, acessos: Dict[str, bool]) -> Tuple[bool, str]:
        """
        Edita um usuário existente
        
        Args:
            usuario_id: ID do usuário
            nome: Nome do usuário
            tipo: Tipo do usuário
            acessos: Dicionário com os acessos permitidos
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Validações
            if not nome or not nome.strip():
                return False, "Nome do usuário é obrigatório"
            
            if tipo not in ['admin', 'comum']:
                return False, "Tipo de usuário inválido"
            
            # Buscar usuário usando repository
            usuario = self.repository.buscar_por_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # Verificar se nome já existe em outro usuário (usando repository)
            if self.repository.verificar_nome_existe(nome.strip(), excluir_id=usuario_id):
                return False, f"Já existe um usuário com o nome '{nome}'"
            
            # Atualizar dados
            usuario.nome = nome.strip()
            usuario.tipo = tipo
            usuario.acesso_clientes = acessos.get('acesso_clientes', False)
            usuario.acesso_produtos = acessos.get('acesso_produtos', False)
            usuario.acesso_pedidos = acessos.get('acesso_pedidos', False)
            usuario.acesso_financeiro = acessos.get('acesso_financeiro', False)
            usuario.acesso_logistica = acessos.get('acesso_logistica', False)
            
            # Usar repository para atualizar
            self.repository.atualizar(usuario)
            
            # Registrar atividade
            self._registrar_atividade(
                tipo_atividade="Edição de Usuário",
                titulo="Usuário Editado",
                descricao=f"Usuário: {nome} - Tipo: {tipo}",
                modulo="Usuários",
                dados_extras={"usuario_id": usuario_id, "nome": nome, "tipo": tipo}
            )
            
            current_app.logger.info(f"Usuário editado: {nome} (ID: {usuario_id})")
            return True, "Usuário editado com sucesso"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao editar usuário: {str(e)}")
            return False, f"Erro ao editar usuário: {str(e)}"
    
    def redefinir_senha_usuario(self, usuario_id: int, nova_senha: str, senha_admin: str) -> Tuple[bool, str]:
        """
        Redefine a senha de um usuário (apenas para admins)
        
        Args:
            usuario_id: ID do usuário
            nova_senha: Nova senha
            senha_admin: Senha do administrador
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Validar senha do admin usando repository
            admins = self.repository.listar_por_tipo('admin')
            if not admins:
                return False, "Nenhum administrador encontrado"
            
            admin = admins[0]
            if not admin.check_senha(senha_admin):
                return False, "Senha do administrador incorreta"
            
            # Validações
            if not nova_senha or not nova_senha.strip():
                return False, "Nova senha é obrigatória"
            
            # Validar política de senha
            validacao, mensagem = self.validar_politica_senha(nova_senha)
            if not validacao:
                return False, mensagem
            
            # Buscar usuário usando repository
            usuario = self.repository.buscar_por_id(usuario_id)
            if not usuario:
                return False, "Usuário não encontrado"
            
            # Redefinir senha
            usuario.set_senha(nova_senha.strip())
            
            # Usar repository para atualizar
            self.repository.atualizar(usuario)
            
            # Registrar atividade
            self._registrar_atividade(
                tipo_atividade="Redefinição de Senha",
                titulo="Senha Redefinida",
                descricao=f"Usuário: {usuario.nome} - Senha redefinida por administrador",
                modulo="Usuários",
                dados_extras={"usuario_id": usuario_id, "nome": usuario.nome}
            )
            
            current_app.logger.info(f"Senha redefinida para usuário {usuario.nome} (ID: {usuario_id}) por admin")
            return True, "Senha redefinida com sucesso"
            
        except Exception as e:
            current_app.logger.error(f"Erro ao redefinir senha: {str(e)}")
            return False, f"Erro ao redefinir senha: {str(e)}"
    
    def verificar_senha_admin(self, senha: str) -> bool:
        """
        Verifica se a senha fornecida é do admin
        
        Args:
            senha: Senha a ser verificada
            
        Returns:
            bool: True se a senha estiver correta
        """
        try:
            admins = self.repository.listar_por_tipo('admin')
            if admins:
                admin = admins[0]
                return admin.check_senha(senha)
            return False
        except Exception as e:
            current_app.logger.error(f"Erro ao verificar senha admin: {str(e)}")
            return False
    
    def autenticar_usuario(self, nome: str, senha: str) -> Optional[Usuario]:
        """
        Autentica um usuário
        
        Args:
            nome: Nome do usuário
            senha: Senha do usuário
            
        Returns:
            Optional[Usuario]: Usuário autenticado ou None
        """
        try:
            usuario = self.repository.buscar_por_nome(nome)
            if usuario and usuario.check_senha(senha):
                return usuario
            return None
        except Exception as e:
            current_app.logger.error(f"Erro ao autenticar usuário: {str(e)}")
            return None
    
    def _registrar_atividade(self, tipo_atividade: str, titulo: str, descricao: str, modulo: str, dados_extras: Dict = None) -> None:
        """
        Registra atividade no log do sistema
        
        Args:
            tipo_atividade: Tipo da atividade
            titulo: Título da atividade
            descricao: Descrição da atividade
            modulo: Módulo onde ocorreu
            dados_extras: Dados extras para o log
        """
        try:
            if 'usuario_id' in session:
                # Converter valores Decimal para float antes da serialização JSON
                if dados_extras:
                    dados_convertidos = {}
                    for key, value in dados_extras.items():
                        if hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                            dados_convertidos[key] = float(value)
                        else:
                            dados_convertidos[key] = value
                    dados_json = json.dumps(dados_convertidos)
                else:
                    dados_json = None
                
                log = LogAtividade(
                    usuario_id=session['usuario_id'],
                    tipo_atividade=tipo_atividade,
                    titulo=titulo,
                    descricao=descricao,
                    modulo=modulo,
                    dados_extras=dados_json
                )
                db.session.add(log)
                db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Erro ao registrar atividade: {e}")
            # Não falhar se o log não puder ser registrado
            pass
