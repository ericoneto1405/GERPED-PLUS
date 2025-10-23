## 🔑 Configuração Inicial

### **Primeiro Acesso - Desenvolvimento**

Para desenvolvimento local, você pode criar um usuário administrador usando o script de inicialização:

```bash
# Opção 1: Criar admin via variáveis de ambiente
export ADMIN_USERNAME=seu_usuario
export ADMIN_PASSWORD=SuaSenhaForte123!
python init_db.py

# Opção 2: Criar admin manualmente via Python
python3 << PYTHON
from meu_app import create_app, db
from meu_app.models import Usuario

app = create_app()
with app.app_context():
    admin = Usuario(
        nome='seu_usuario',
        senha_hash='',
        tipo='admin',
        acesso_clientes=True,
        acesso_produtos=True,
        acesso_pedidos=True,
        acesso_financeiro=True,
        acesso_logistica=True
    )
    admin.set_senha('SuaSenhaForte123!')
    db.session.add(admin)
    db.session.commit()
    print('✓ Usuário admin criado com sucesso!')
PYTHON
```

⚠️ **IMPORTANTE:** 
- NUNCA use senhas fracas ou padrão (como admin123)
- Em desenvolvimento, use senhas fortes mesmo que temporárias
- Em produção, use senhas complexas com 16+ caracteres

### **Primeiro Acesso - Produção**

Em produção, crie o usuário administrador de forma segura:

1. **Configure variáveis de ambiente:**
```bash
export FLASK_ENV=production
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="postgresql://user:pass@host/db"
export ADMIN_USERNAME="admin_producao"
export ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

2. **Execute a inicialização:**
```bash
python init_db.py
```

3. **IMPORTANTE:** Anote as credenciais em local seguro (gerenciador de senhas)

4. **Após primeiro login, altere a senha pelo painel de usuários**

---

## 🔒 Segurança - Boas Práticas

### **NUNCA faça:**
- ❌ Commitar credenciais no código
- ❌ Usar senhas padrão (admin, admin123, etc.)
- ❌ Reutilizar senhas entre ambientes
- ❌ Compartilhar credenciais via e-mail/chat
- ❌ Manter credenciais de desenvolvimento em produção

### **SEMPRE faça:**
- ✅ Use senhas fortes (16+ caracteres, aleatórias)
- ✅ Armazene credenciais em gerenciador de senhas
- ✅ Use variáveis de ambiente para configuração
- ✅ Rotacione senhas periodicamente
- ✅ Habilite HTTPS em produção
- ✅ Configure 2FA quando disponível
- ✅ Revise logs de acesso regularmente

---
