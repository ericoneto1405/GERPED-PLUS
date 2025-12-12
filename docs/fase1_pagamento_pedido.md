# FASE 1 – Diagnóstico da página “Pagamento do Pedido”

## Objetivos cumpridos
1. Inventariar a estrutura visual e os componentes existentes no template `meu_app/templates/lancar_pagamento.html`.
2. Mapear dependências externas (CSS global, scripts, rotas e serviços) que impactam o comportamento atual.
3. Consolidar os principais pontos fortes, dores e prioridades que irão direcionar as próximas fases.

## Inventário visual e estrutural
- **Shell principal** (`meu_app/templates/lancar_pagamento.html:1-574`): define toda a paleta (`--surface`, `--border`, etc.), cartões, grids, botões e responsividade com CSS inline.
- **Resumo do pedido** (`meu_app/templates/lancar_pagamento.html:602-625`): cartão com grid de quatro colunas exibindo Cliente, Total, Pago e Saldo (inclui pill de status).
- **Formulário de pagamento** (`meu_app/templates/lancar_pagamento.html:627-736`): dois fieldsets (Pagamento e Comprovante) com `input-grid`, dropzone, fila de comprovantes, toggle de compartilhamento e campos ocultos.
- **Painel lateral** (`meu_app/templates/lancar_pagamento.html:739-755`): checklist de revisão e histórico de pagamentos anteriores no mesmo cartão.
- **Scripts** (`meu_app/templates/lancar_pagamento.html:763-795`): lógica inline para mensagens flash + import do bundle `static/js/financeiro_pagamento.js`.

## Dependências identificadas
- **CSS global**: apesar de `base.html` carregar `static/style.css`, a página não estende o layout principal; todo o estilo está embutido, o que cria duplicidade com o tema global.
- **JavaScript**: `meu_app/static/js/financeiro_pagamento.js` consome atributos `data-*` (OCR, comprovantes compartilhados) e manipula elementos com seletores específicos (`.fila-lista`, `.comprovante-panel`). Qualquer refatoração precisa preservar esses hooks.
- **Back-end / rotas**: blueprint `financeiro_bp` em `meu_app/financeiro/routes.py` fornece endpoints usados no formulário (`processar_recibo_ocr`, `api_comprovantes_compartilhados`, etc.) e injeta dados (`total`, `pago`, `saldo`, `pedido`).

## Insights principais
### Pontos positivos
- Estrutura semântica consistente (uso de `<section>`, `<fieldset>`, `<legend>`, `<aside>`).
- Layout modular dividido em cartão de resumo, formulário e painel lateral — facilita a extração futura para componentes.

### Pontos negativos
- CSS inline extenso dificulta manutenção e reaproveitamento; qualquer mudança visual precisa duplicar estilos.
- A `input-grid` e o campo “Observações” dependem de ajustes ad hoc, indicando ausência de sistema de espaçamento/breakpoints reutilizáveis.
- Seção de comprovantes mistura upload, OCR, fila e compartilhamento no mesmo bloco visual, o que aumenta a carga cognitiva.

## Recomendações para a Fase 2
1. **Externalizar estilos**: mover tokens, cartões e grids para um arquivo dedicado (ex.: `static/css/financeiro_pagamento.css`) e importar via `base.html` ou `<link>` local.
2. **Normalizar componentes**: criar variantes de `section-card`, `input-group` e `ghost-btn` para uso em todo o módulo Financeiro, reduzindo CSS redundante.
3. **Desacoplar a área de comprovantes**: separar visualmente (ou em componentes menores) o upload, a fila e o painel de compartilhamento para facilitar futuras melhorias e garantir compatibilidade com o JS existente.

Esses entregáveis encerram a FASE 1 e preparam a próxima etapa de consolidação dos estilos compartilhados.
