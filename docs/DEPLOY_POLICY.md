# Politica de Publicacao (Revisao Obrigatoria)

Objetivo:
- manter `auto-push` ativo;
- impedir publicacao automatica em producao sem revisao humana.

## Como fica o fluxo

1. `auto_git_commit.py` cria commit local automaticamente.
2. O push vai para `origin/review/autocommit` (nao para `main`).
3. Revisao ocorre via Pull Request.
4. Apenas depois do merge em `main`, a mudanca fica elegivel para producao.

## Configuracao usada

- `AUTO_COMMIT_PRODUCTION_BRANCH=main`
- `AUTO_COMMIT_PUSH_BRANCH=review/autocommit`

Essas variaveis estao no arquivo:
- `com.sistema-gerped.autocommit.plist`

## Recomendacoes no GitHub

1. Ativar Branch Protection em `main`:
- Require a pull request before merging
- Require approvals (minimo 1)
- Dismiss stale approvals on new commits
- Restrict who can push to matching branches

2. Deploy de producao:
- Nao executar deploy por webhook em push.
- Fazer deploy apenas apos aprovacao humana (manual).

