# 🔐 Pipeline de Segurança (Fase 5)

Este documento descreve os scanners automatizados adicionados ao repositório.

## 1. Workflow `Security Scans`

Arquivo: `.github/workflows/security-scans.yml`

### Semgrep
- Executa `semgrep ci --config p/default` em todos os pushes/PRs.
- Para regras específicas, altere a variável `--config` (ex.: `p/flask` ou arquivos locais).
- Saída falhará o job se forem encontrados achados de severidade alta/média.

### Snyk (opcional)
- Requer o secret `SNYK_TOKEN` configurado no repositório.
- Quando presente, o passo `Run Snyk` executa `snyk test` em `requirements.txt`.
- Para ignorar vulnerabilidades específicas, use `snyk ignore` localmente e commite `.snyk`.

## 2. Como habilitar
1. Configure `SEMGREP_RULES` ou crie regras customizadas em `semgrep-rules/` se necessário.
2. Adicione o secret `SNYK_TOKEN` nas configurações do repositório.
3. Opcional: adicione `SNYK_ORG`, `SNYK_SEVERITY_THRESHOLD`, etc., conforme a política da empresa.

## 3. Execução local
```bash
pip install semgrep snyk
semgrep ci --config p/default
SNYK_TOKEN=xxxx snyk test --file=requirements.txt --package-manager=pip
```

## 4. Próximos passos sugeridos
- Integrar relatórios ao pipeline principal (ex.: upload como artefato).
- Adicionar alertas no Slack/Teams usando webhooks quando um job falhar.
- Revisar resultados periodicamente e criar issues/lidas técnicas.
