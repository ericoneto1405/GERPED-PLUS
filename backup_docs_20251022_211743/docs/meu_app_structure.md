# Estrutura da pasta `meu_app`

Este documento existe para contornar um problema intermitente no viewer web do GitHub, que às vezes falha ao renderizar o diretório `meu_app/`. Abaixo está uma visão geral manual da árvore de arquivos relevante para a arquitetura da aplicação.

## Visão geral (até 2 níveis)

```text
meu_app
├── __init__.py
├── apuracao
│   ├── factory.py
│   ├── interfaces.py
│   ├── repositories.py
│   ├── routes.py
│   └── services.py
├── clientes
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── coletas
│   ├── receipt_service.py
│   ├── routes.py
│   ├── schemas.py
│   └── services/
├── estoques
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── financeiro
│   ├── config.py
│   ├── exceptions.py
│   ├── ocr_service.py
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   ├── services.py
│   └── vision_service.py
├── log_atividades
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── pedidos
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── produtos
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── usuarios
│   ├── repositories.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
└── vendedor
    ├── routes.py
    ├── schemas.py
    └── services.py
```

## Como gerar a árvore localmente

Caso precise atualizar ou validar esta estrutura depois de alterações:

```bash
tree -L 2 meu_app
```

## Observações sobre a arquitetura

- Cada domínio (`clientes`, `pedidos`, `produtos`, etc.) possui pares `repositories.py`, `schemas.py` (quando necessário) e `services.py`, mantendo regra de negócio fora das views.
- Os módulos `routes.py` de cada domínio expõem apenas endpoints e delegam lógica para camadas de serviço ou repositório.
- Serviços compartilhados (por exemplo, `decorators.py`, `validators.py`, `upload_security.py`) permanecem na raiz para evitar dependências cíclicas entre domínios.
- O módulo `coletas` mantém múltiplas implementações sob `services/` (`coleta_service.py`, histórico, etc.) para organizar fluxos específicos sem poluir as views.

Com esses detalhes é possível auditar a organização da pasta sem depender do carregamento do diretório pelo viewer do GitHub.
