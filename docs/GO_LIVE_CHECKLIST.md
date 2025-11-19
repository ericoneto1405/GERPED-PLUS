# 🚀 Checklist de Go-Live

## Configuração
- [ ] `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL` definidos em secrets seguros.
- [ ] `DATABASE_REQUIRE_SSL=True` para bancos gerenciados.
- [ ] Variáveis `LOGIN_MAX_ATTEMPTS` e `LOGIN_LOCKOUT_SECONDS` ajustadas conforme política.

## Infraestrutura
- [ ] Executar `make install` e `make migrate` no ambiente final.
- [ ] Verificar healthchecks: `curl /healthz` e `/readiness`.
- [ ] Habilitar HTTPS + proxy (Nginx/Apache) com certificados válidos.

## Observabilidade e Logs
- [ ] Garantir rotação de logs (`LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`).
- [ ] Configurar agregação externa (ELK, CloudWatch) se necessário.
- [ ] Confirmar que dados sensíveis estão mascarados (CPF, CNPJ, pix) via novo formatter.

## Segurança
- [ ] Executar `make security` localmente.
- [ ] Confirmar pipeline `Security Scans` passando no PR.
- [ ] Revisar permissões de usuários administrativos.

## Backups e DR
- [ ] Configurar backups automáticos do banco (dump ou snapshots).
- [ ] Testar restauração em ambiente separado.
- [ ] Verificar política de retenção para recibos/PDFs.

## Operação
- [ ] Registrar procedimentos de start/stop (`make server-start`, `make server-status`).
- [ ] Adicionar monitoramento de métricas Prometheus / alertas.
- [ ] Validar plano de comunicação em caso de incidentes (contatos, canais).
