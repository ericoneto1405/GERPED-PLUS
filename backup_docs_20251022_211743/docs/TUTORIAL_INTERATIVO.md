# TUTORIAL INTERATIVO - SISTEMA DE APURAÇÃO FINANCEIRA

## 🎯 **OBJETIVO DO TUTORIAL**

Este tutorial interativo irá guiá-lo através de um **fluxo completo** de trabalho no sistema, desde o cadastro básico até a geração de relatórios finais.

**Tempo estimado**: 30-45 minutos
**Nível**: Iniciante a Intermediário
**Pré-requisitos**: Sistema rodando em http://localhost:5004

---

## 🚀 **PREPARAÇÃO INICIAL**

### **Passo 1: Iniciar o Sistema**
```bash
# No terminal, navegue para a pasta do projeto
cd /Users/ericobrandao/Downloads/SAP

# Execute o sistema
python3 run.py
```

**✅ Resultado esperado:**
```
 * Serving Flask app 'meu_app'
 * Debug mode: off
 * Running on http://127.0.0.1:5004
```

### **Passo 2: Acessar o Sistema**
1. Abra seu navegador
2. Digite: `http://localhost:5004`
3. Faça login com suas credenciais

**✅ Você deve ver:**
- Logo do Sistema de Apuração Financeira
- Menu de navegação no topo
- Dashboard principal

---

## 📚 **CENÁRIO COMPLETO: VENDA COMPLETA**

Vamos simular um **fluxo completo de venda**, desde o cadastro do cliente até a apuração financeira.

### **🎬 CENÁRIO:**
- **Cliente**: João Silva (novo cliente)
- **Produto**: Notebook Dell Inspiron (novo produto)
- **Pedido**: 2 notebooks por R$ 3.500,00 cada
- **Pagamento**: PIX no ato
- **Apuração**: Agosto/2025

---

## 👥 **ETAPA 1: CADASTRAR CLIENTE**

### **Passo 1: Acessar Módulo de Clientes**
1. No menu principal, clique em **"Clientes"**
2. Clique no botão **"Novo Cliente"**

**✅ Você deve ver:**
- Formulário de cadastro de cliente
- Campos obrigatórios marcados com *

### **Passo 2: Preencher Dados do Cliente**
```
Nome: João Silva
CPF: 123.456.789-00
Telefone: (11) 99999-9999
Email: joao.silva@email.com
Endereço: Rua das Flores, 123 - São Paulo/SP
```

### **Passo 3: Salvar Cliente**
1. Clique em **"Salvar"**
2. **✅ Confirmação esperada**: "Cliente cadastrado com sucesso!"

**🎯 DICA**: Anote o ID do cliente criado para usar nas próximas etapas.

---

## 🛍️ **ETAPA 2: CADASTRAR PRODUTO**

### **Passo 1: Acessar Módulo de Produtos**
1. No menu principal, clique em **"Produtos"**
2. Clique no botão **"Novo Produto"**

### **Passo 2: Preencher Dados do Produto**
```
Nome: Notebook Dell Inspiron
Descrição: Notebook Dell Inspiron 15" Intel i5 8GB 256GB SSD
Categoria: Eletrônicos
Preço de Venda: 3.500,00
Preço de Custo: 2.800,00
Unidade: UN
```

### **Passo 3: Salvar Produto**
1. Clique em **"Salvar"**
2. **✅ Confirmação esperada**: "Produto cadastrado com sucesso!"

**🎯 DICA**: Anote o ID do produto criado para usar nas próximas etapas.

---

## 📦 **ETAPA 3: ATUALIZAR ESTOQUE**

### **Passo 1: Acessar Módulo de Estoques**
1. No menu principal, clique em **"Estoques"**
2. Clique no botão **"Adicionar ao Estoque"**

### **Passo 2: Preencher Dados do Estoque**
```
Produto: Notebook Dell Inspiron (selecione na lista)
Quantidade: 5
Status: Disponível
Observações: Estoque inicial
```

### **Passo 3: Salvar Estoque**
1. Clique em **"Salvar"**
2. **✅ Confirmação esperada**: "Estoque atualizado com sucesso!"

**🎯 DICA**: Verifique se o produto aparece na lista de estoques com quantidade 5.

---

## 📋 **ETAPA 4: CRIAR PEDIDO**

### **Passo 1: Acessar Módulo de Pedidos**
1. No menu principal, clique em **"Pedidos"**
2. Clique no botão **"Novo Pedido"**

### **Passo 2: Preencher Dados do Pedido**
```
Cliente: João Silva (selecione na lista)
Data: [Data atual]
Observações: Pedido realizado via telefone
```

### **Passo 3: Adicionar Itens**
1. Clique em **"Adicionar Item"**
2. Preencha:
   ```
   Produto: Notebook Dell Inspiron
   Quantidade: 2
   Preço Unitário: 3.500,00
   ```
3. Clique em **"Adicionar Item"**

**✅ Resultado esperado:**
- Item aparece na lista de itens
- Total do pedido: R$ 7.000,00

### **Passo 4: Salvar Pedido**
1. Clique em **"Salvar Pedido"**
2. **✅ Confirmação esperada**: "Pedido criado com sucesso!"

**🎯 DICA**: Anote o número do pedido criado.

---

## 💰 **ETAPA 5: REGISTRAR PAGAMENTO**

### **Passo 1: Acessar o Pedido**
1. Na lista de pedidos, clique no **botão "VER"** do pedido criado
2. Clique em **"Registrar Pagamento"**

### **Passo 2: Preencher Dados do Pagamento**
```
Valor: 7.000,00
Forma: PIX
Data: [Data atual]
Observações: Pagamento realizado no ato
```

### **Passo 3: Salvar Pagamento**
1. Clique em **"Salvar"**
2. **✅ Confirmação esperada**: "Pagamento registrado com sucesso!"

**🎯 DICA**: Verifique se o status do pedido mudou para "Pago".

---

## 📊 **ETAPA 6: CRIAR APURAÇÃO FINANCEIRA**

### **Passo 1: Acessar Módulo de Apuração**
1. No menu principal, clique em **"Apuração"**
2. Clique no botão **"Nova Apuração"**

### **Passo 2: Calcular Dados do Período**
1. Clique em **"Calcular Dados do Período"**
2. Preencha:
   ```
   Mês: 8 (Agosto)
   Ano: 2025
   ```
3. Clique em **"Calcular"**

**✅ Resultado esperado:**
- Receita calculada: R$ 7.000,00
- CPV calculado: R$ 5.600,00 (2 × R$ 2.800,00)
- Total de pedidos: 1

### **Passo 3: Preencher Dados da Apuração**
```
Mês: 8
Ano: 2025
Receita: 7.000,00 (usar valor calculado)
CPV: 5.600,00 (usar valor calculado)
Verba SCANN: 200,00
Outros Custos: 100,00
```

### **Passo 4: Salvar Apuração**
1. Clique em **"Salvar"**
2. **✅ Confirmação esperada**: "Apuração criada com sucesso!"

**🎯 DICA**: A apuração será criada com status "Pendente".

---

## 🔍 **ETAPA 7: VERIFICAR RESULTADOS**

### **Passo 1: Verificar Dashboard**
1. Volte ao menu principal
2. Clique em **"Dashboard"**

**✅ Você deve ver:**
- Total de pedidos: 1
- Receita total: R$ 7.000,00
- CPV total: R$ 5.600,00
- Margem bruta: R$ 1.400,00

### **Passo 2: Verificar Lista de Apurações**
1. Menu → **"Apuração"**
2. **✅ Você deve ver:**
   - Apuração de Agosto/2025
   - Status: Pendente
   - Receita: R$ 7.000,00

### **Passo 3: Verificar Estoque Atualizado**
1. Menu → **"Estoques"**
2. **✅ Você deve ver:**
   - Notebook Dell Inspiron
   - Estoque atual: 3 (5 - 2 vendidos)

---

## 📈 **ETAPA 8: GERAR RELATÓRIOS**

### **Passo 1: Relatório de Vendas**
1. No módulo de pedidos
2. Clique em **"Relatórios"**
3. Selecione **"Vendas por Período"**
4. Configure:
   ```
   Período: Agosto/2025
   Formato: PDF
   ```
5. Clique em **"Gerar"**

### **Passo 2: Relatório de Estoque**
1. No módulo de estoques
2. Clique em **"Relatórios"**
3. Selecione **"Posição de Estoque"**
4. Clique em **"Gerar"**

### **Passo 3: Relatório de Apuração**
1. No módulo de apuração
2. Clique em **"Relatórios"**
3. Selecione **"Apuração Mensal"**
4. Configure:
   ```
   Mês: Agosto
   Ano: 2025
   ```
5. Clique em **"Gerar"**

---

## 🎯 **ETAPA 9: TORNAR APURAÇÃO DEFINITIVA**

### **Passo 1: Acessar Apuração**
1. Na lista de apurações
2. Clique na apuração de Agosto/2025

### **Passo 2: Tornar Definitiva**
1. Clique em **"Tornar Definitiva"**
2. Confirme a ação
3. **✅ Confirmação esperada**: "Apuração tornada definitiva com sucesso!"

**⚠️ ATENÇÃO**: Apuração definitiva não pode mais ser editada!

---

## 🔍 **ETAPA 10: VALIDAÇÃO FINAL**

### **Verificações Obrigatórias:**

#### **✅ Cliente:**
- [ ] João Silva cadastrado
- [ ] Dados completos e corretos

#### **✅ Produto:**
- [ ] Notebook Dell Inspiron cadastrado
- [ ] Preços configurados corretamente

#### **✅ Estoque:**
- [ ] Quantidade inicial: 5
- [ ] Quantidade após venda: 3
- [ ] Histórico de movimentação registrado

#### **✅ Pedido:**
- [ ] Pedido criado com 2 notebooks
- [ ] Total: R$ 7.000,00
- [ ] Status: Pago
- [ ] Pagamento registrado

#### **✅ Apuração:**
- [ ] Dados calculados automaticamente
- [ ] Receita: R$ 7.000,00
- [ ] CPV: R$ 5.600,00
- [ ] Status: Definitiva

---

## 🎉 **PARABÉNS! TUTORIAL CONCLUÍDO**

### **O que você aprendeu:**
1. ✅ **Cadastro completo** de cliente e produto
2. ✅ **Gestão de estoque** com histórico
3. ✅ **Criação de pedidos** com itens
4. ✅ **Registro de pagamentos** e controle de status
5. ✅ **Cálculo automático** de dados financeiros
6. ✅ **Criação de apurações** com validação
7. ✅ **Geração de relatórios** em diferentes formatos
8. ✅ **Controle de status** (pendente/definitiva)

### **Próximos passos recomendados:**
1. **Experimente** com diferentes cenários
2. **Explore** outros módulos do sistema
3. **Teste** funcionalidades avançadas
4. **Consulte** a documentação completa
5. **Entre em contato** com suporte se necessário

---

## 🚨 **SOLUÇÃO DE PROBLEMAS COMUNS**

### **Problema: "Cliente não encontrado"**
**Solução**: Verifique se o cliente foi salvo corretamente na Etapa 1

### **Problema: "Produto não encontrado"**
**Solução**: Verifique se o produto foi salvo corretamente na Etapa 2

### **Problema: "Estoque insuficiente"**
**Solução**: Verifique se o estoque foi atualizado na Etapa 3

### **Problema: "Erro ao calcular dados"**
**Solução**: Verifique se o pedido está com status "Pago"

### **Problema: "Apuração não salva"**
**Solução**: Verifique se todos os campos obrigatórios estão preenchidos

---

## 📞 **PRECISA DE AJUDA?**

### **Canais de Suporte:**
- **Email**: suporte@sistema.com
- **Telefone**: (11) 9999-9999
- **Chat**: Sistema integrado
- **Documentação**: docs/ (pasta de documentação)

### **Recursos Adicionais:**
- **Guia do Usuário**: docs/GUIA_USUARIO.md
- **Documentação Técnica**: docs/FASE7_DOCUMENTACAO_COMPLETA.md
- **Guia do Desenvolvedor**: docs/GUIA_DESENVOLVEDOR.md

---

**© 2025 Sistema de Apuração Financeira - Tutorial Interativo**
