# 📊 Módulo de Análise de Necessidade de Compra

## Visão Geral

O módulo de **Análise de Necessidade de Compra** é uma ferramenta poderosa que analisa automaticamente o estoque atual, pedidos pendentes e histórico de vendas para sugerir quais produtos precisam ser adquiridos e em qual quantidade.

## Características

### ✨ Funcionalidades Principais

- **Análise Automática**: Calcula automaticamente a necessidade de compra baseada em:
  - Estoque atual
  - Pedidos pendentes (status: Pendente ou Pagamento Aprovado)
  - Histórico de vendas dos últimos 30 dias
  - Margem de segurança configurável

- **Classificação por Status**:
  - 🔴 **Crítico**: Produtos com estoque zero e pedidos pendentes
  - 🟡 **Alerta**: Produtos com estoque baixo e necessidade de compra
  - 🟢 **Normal**: Produtos com estoque adequado

- **Cálculo Inteligente**:
  - Considera margem de segurança (padrão: 20%)
  - Opção de incluir histórico de vendas
  - Cálculo automático de valor total necessário
  - Preço médio de compra por produto

- **Exportação**: Gera lista de compras em formato TXT para impressão ou compartilhamento

### 📍 Acesso

**URL**: `/necessidade-compra`

**Menu**: Sistema SAP → Análise de Compra

**Permissões**: Admin ou usuários com acesso a Produtos

## Arquitetura do Módulo

```
meu_app/necessidade_compra/
├── __init__.py          # Blueprint e inicialização
├── schemas.py           # Schemas Pydantic para validação
├── repositories.py      # Camada de acesso a dados
├── services.py          # Lógica de negócio
└── routes.py            # Endpoints e rotas

meu_app/templates/necessidade_compra/
└── dashboard.html       # Interface visual
```

## API Endpoints

### 1. Dashboard Principal
```
GET /necessidade-compra/
```
Interface visual para análise de necessidades

### 2. Analisar Necessidades
```
GET /necessidade-compra/api/analisar
```

**Query Parameters**:
- `margem_seguranca` (int, opcional): Percentual de margem de segurança (0-100, padrão: 20)
- `considerar_historico` (bool, opcional): Se deve considerar histórico de vendas (padrão: true)

**Response**:
```json
{
  "success": true,
  "analises": [
    {
      "produto_id": 1,
      "produto_nome": "Produto Exemplo",
      "estoque_atual": 10,
      "quantidade_pedidos_pendentes": 50,
      "quantidade_necessaria": 40,
      "sugestao_compra": 48,
      "preco_medio_compra": 25.50,
      "valor_total_sugerido": 1224.00,
      "status": "alerta"
    }
  ],
  "resumo": {
    "total_produtos": 150,
    "produtos_criticos": 5,
    "produtos_alerta": 12,
    "valor_total_necessario": 15430.50
  },
  "parametros": {
    "margem_seguranca": 20,
    "considerar_historico": true
  }
}
```

### 3. Exportar Lista de Compras
```
POST /necessidade-compra/api/exportar
```

**Body**:
```json
{
  "analises": [...],
  "apenas_necessarios": true
}
```

**Response**: Arquivo TXT para download

### 4. Resumo Rápido
```
GET /necessidade-compra/api/resumo
```

Retorna apenas o resumo da análise (mais rápido)

## Como Funciona

### Algoritmo de Cálculo

1. **Coleta de Dados**:
   - Estoque atual de cada produto
   - Soma de quantidades em pedidos pendentes
   - Histórico de vendas dos últimos 30 dias (opcional)

2. **Cálculo de Necessidade**:
   ```
   Necessidade Base = Pedidos Pendentes - Estoque Atual
   ```

3. **Adição de Histórico** (se habilitado):
   ```
   Média Diária = Total Vendido (30 dias) / 30
   Projeção 15 dias = Média Diária × 15
   Necessidade Total = Necessidade Base + Projeção 15 dias
   ```

4. **Margem de Segurança**:
   ```
   Sugestão Final = Necessidade Total × (1 + Margem/100)
   ```

5. **Classificação de Status**:
   - **Crítico**: Necessidade > 0 E Estoque = 0
   - **Alerta**: Necessidade > 0 E Estoque > 0
   - **Normal**: Necessidade ≤ 0

## Interface do Usuário

### Controles

- **Margem de Segurança**: Slider de 0-100% para ajustar a margem
- **Considerar Histórico**: Checkbox para incluir análise histórica
- **Botão Analisar**: Executa a análise com os parâmetros selecionados

### Cards de Resumo

- 📦 **Total de Produtos**: Quantidade total analisada
- 🔴 **Produtos Críticos**: Produtos com estoque zero
- 🟡 **Produtos em Alerta**: Produtos com estoque baixo
- 💰 **Valor Total Necessário**: Investimento total estimado

### Tabela de Resultados

Exibe para cada produto:
- Status (badge colorido)
- Nome do produto
- Estoque atual
- Pedidos pendentes
- Quantidade necessária
- Sugestão de compra
- Preço médio
- Valor total

### Filtros Rápidos

- **Todos**: Exibe todos os produtos
- **Críticos**: Apenas produtos críticos
- **Alertas**: Apenas produtos em alerta
- **Normais**: Apenas produtos normais

## Exemplos de Uso

### Exemplo 1: Análise Padrão
```bash
curl "http://localhost:5004/necessidade-compra/api/analisar"
```

### Exemplo 2: Análise com Margem Customizada
```bash
curl "http://localhost:5004/necessidade-compra/api/analisar?margem_seguranca=30"
```

### Exemplo 3: Análise sem Histórico
```bash
curl "http://localhost:5004/necessidade-compra/api/analisar?considerar_historico=false"
```

### Exemplo 4: Exportar Lista
```bash
curl -X POST "http://localhost:5004/necessidade-compra/api/exportar" \
  -H "Content-Type: application/json" \
  -d '{"analises": [...], "apenas_necessarios": true}' \
  --output lista_compras.txt
```

## Integração com Outros Módulos

### Dependências

- **Produtos**: Obtém informações de produtos e preços médios
- **Estoques**: Consulta quantidades em estoque
- **Pedidos**: Verifica pedidos pendentes
- **ItemPedido**: Calcula totais de itens pendentes

### Modelos Utilizados

- `Produto`: Informações do produto
- `Estoque`: Quantidades em estoque
- `Pedido`: Status de pedidos
- `ItemPedido`: Itens dos pedidos
- `StatusPedido`: Enum para status de pedidos

## Segurança

- ✅ Requer autenticação (`@login_required`)
- ✅ Verifica permissões de acesso a produtos
- ✅ Proteção CSRF habilitada
- ✅ Rate limiting aplicado
- ✅ Validação de parâmetros com Pydantic

## Performance

### Otimizações

- Queries SQL otimizadas com JOINs e subqueries
- Uso de `func.coalesce()` para evitar NULLs
- Caching de resultados (opcional)
- Loading assíncrono na interface

### Considerações

- Para bases com muitos produtos (>1000), considere adicionar paginação
- O histórico de vendas pode ser pesado em bases grandes
- Recomenda-se executar análises fora de horário de pico

## Troubleshooting

### Problema: Análise muito lenta
**Solução**: 
- Desabilite "Considerar histórico"
- Verifique índices nas tabelas: `produto`, `estoque`, `pedido`, `item_pedido`
- Considere adicionar cache

### Problema: Valores incorretos
**Solução**:
- Verifique se os preços médios estão cadastrados nos produtos
- Confirme que os pedidos têm status corretos
- Valide as quantidades em estoque

### Problema: Não aparece no menu
**Solução**:
- Verifique as permissões do usuário
- Confirme que o blueprint foi registrado
- Verifique o log do servidor

## Roadmap Futuro

- [ ] Suporte a fornecedores preferenciais
- [ ] Integração com sistema de compras
- [ ] Alertas automáticos por e-mail
- [ ] Gráficos de tendência de consumo
- [ ] Exportação em Excel/CSV
- [ ] Análise por categoria de produto
- [ ] Previsão baseada em IA/ML

## Manutenção

### Logs
```bash
tail -f instance/logs/server.log | grep "necessidade_compra"
```

### Testes
```bash
pytest tests/necessidade_compra/
```

### Linting
```bash
ruff check meu_app/necessidade_compra/
black meu_app/necessidade_compra/
```

## Suporte

Para dúvidas ou problemas:
1. Consulte os logs em `instance/logs/server.log`
2. Verifique a documentação da API em `/docs`
3. Revise este documento

---

**Versão**: 1.0.0  
**Data**: Outubro 2025  
**Autor**: Sistema SAP

