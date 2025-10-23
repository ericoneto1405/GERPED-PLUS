# Logging Centralizado com Grafana & Loki

Este diretório contém os arquivos-base para habilitar a coleta e visualização
centralizada de logs do sistema SAP durante o go-live.

## Visão Geral da Arquitetura

```
Sistema SAP  ──► Promtail ──► Loki ──► Grafana
                              │
                              └──► Alertmanager ──► Telegram/E-mail
```

- **Promtail** coleta logs locais (`instance/logs/*.log`) e envia para o Loki.
- **Loki** armazena e indexa os logs.
- **Grafana** permite dashboards e alertas.
- **Alertmanager** (opcional) envia notificações para canais configurados.

## Pré-requisitos

- Docker e Docker Compose instalados e em execução.
- Conta/canal configurados para Telegram (ou servidor SMTP) para os alertas.

## Passos para Deploy Local

1. Ajuste variáveis de ambiente no arquivo `.env` (crie a partir deste template):

```
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=trocar-senha
TELEGRAM_BOT_TOKEN=coloque-token
TELEGRAM_CHAT_ID=coloque-chat-id
EMAIL_SMTP_HOST=smtp.exemplo.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=alertas@suaempresa.com
EMAIL_TO=devops@suaempresa.com
EMAIL_USERNAME=usuario
EMAIL_PASSWORD=senha
```

2. Suba a stack:

```bash
docker compose -f infrastructure/logging/docker-compose.yml up -d
```

3. Acesse o Grafana: `http://localhost:3000`

4. Importe o dashboard `dashboard_go_live.json` (quando houver) ou crie um dashboard
   com os painéis desejados.

## Alertas

- Para Telegram: configure o contato no `alertmanager.yml`.
- Para e-mail: habilite a rota `email` no mesmo arquivo.
- As regras de alerta vivem em `alert-rules.yml`. Há uma regra exemplo que dispara
  quando existir log com severidade `ERROR` em menos de 5 minutos.

## Envio de Logs

- O `promtail-config.yml` já aponta para `instance/logs/`. Ajuste caminhos conforme necessário.
- Para adicionar novos arquivos, inclua novos `static_configs` ou `pipeline_stages`.

## Produção

1. Ajuste os volumes para apontar para discos persistentes (EBS, NFS, etc.).
2. Proteja o Grafana por VPN/SAML/SSO.
3. Configure backup periódico dos diretórios de dados (`loki`, `grafana`).
4. Habilite HTTPS com um proxy reverso (nginx/traefik) em frente ao Grafana.

## Limpeza

```bash
docker compose -f infrastructure/logging/docker-compose.yml down -v
```

> Nota: Este setup serve como base inicial. Adeque limites de retenção, escalabilidade
> e autenticação conforme as necessidades da sua operação.
