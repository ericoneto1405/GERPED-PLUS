# ==============================================================================
# Dockerfile - Sistema SAP (Hardened)
# ==============================================================================

# Build stage
FROM python:3.9-alpine AS builder

# Instalar dependências de build
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    openssl-dev

# Criar usuário não-root
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Runtime stage
FROM python:3.9-alpine

# Metadados
LABEL maintainer="Sistema SAP"
LABEL version="2.0"
LABEL description="Sistema de Gestão Empresarial SAP - Hardened"

# Instalar apenas dependências runtime
RUN apk add --no-cache \
    postgresql-libs \
    libmagic \
    curl  # Para healthcheck

# Criar usuário não-root
RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

# Configurar diretórios
WORKDIR /app
RUN mkdir -p /app/instance/logs /app/instance/backups /app/uploads && \
    chown -R appuser:appgroup /app

# Copiar dependências do builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copiar código da aplicação
COPY --chown=appuser:appgroup . /app/

# Adicionar .local/bin ao PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Variáveis de ambiente
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expor porta
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/healthz || exit 1

# Mudar para usuário não-root
USER appuser

# Comando padrão
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]

