# 🚀 Guia de Implantação no Neon (PostgreSQL Serverless)

Este passo a passo mostra como apontar o Sistema SAP para um banco PostgreSQL gratuito usando o **Neon**.

## 1. Criar o banco

1. Acesse [https://neon.tech](https://neon.tech) e crie uma conta (plano *Free Tier*).
2. Crie um projeto e mantenha o *branch* padrão `main`.
3. No painel do projeto, copie a string `psql` ou `connection string` no formato:
   ```
   postgresql://usuario:senha@ep-xxxx.neon.tech:5432/neondb
   ```
   > Ela já vem com `sslmode=require`. Se não vier, adicione manualmente (`...?sslmode=require`).

## 2. Configurar variáveis de ambiente

No `.env` (ou variáveis do serviço onde o app roda):

```env
FLASK_ENV=production
SECRET_KEY=<chave forte gerada com secrets.token_hex>
DATABASE_URL=postgresql://usuario:senha@ep-xxxx.neon.tech:5432/neondb?sslmode=require
DATABASE_REQUIRE_SSL=True
REDIS_URL=<opcional, se usar Redis>
```

> `DATABASE_REQUIRE_SSL` garante que o app sempre force TLS quando conectado a serviços gerenciados.

## 3. Rodar migrations

No servidor/CI com o `.env` configurado:

```bash
source venv/bin/activate  # se estiver usando virtualenv
pip install -r requirements.txt
FLASK_ENV=production make migrate
```

Isso cria todo o schema no banco Neon.

## 4. Verificar conexão

1. `python -c "import sqlalchemy; from config import ProductionConfig; print(ProductionConfig.SQLALCHEMY_DATABASE_URI)"`
2. Rode `make test-fast` para garantir que os modelos conseguem acessar o banco.
3. No painel do Neon, abra o SQL Editor e execute `SELECT * FROM alembic_version;` para confirmar que a migration foi aplicada.

## 5. Backups e boas práticas

- O Neon já cria *snapshots* automáticos, mas exporte dumps periódicos (`pg_dump $DATABASE_URL`).
- Use *branches* separados (ex.: `staging`) para ambientes diferentes.
- Ajuste limites de conexão no Neon se planeja usar muitos workers Gunicorn.

Pronto! O Sistema SAP agora usa um banco PostgreSQL gerenciado gratuitamente, mantendo TLS obrigatório e migrações controladas pelo Alembic.
