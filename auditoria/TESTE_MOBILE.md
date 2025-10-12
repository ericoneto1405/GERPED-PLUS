# 📱 GUIA DE TESTE - Responsividade Mobile

## 🚀 Teste Rápido (2 minutos)

### 1. Abrir DevTools Mobile
```
Chrome: F12 > Ctrl+Shift+M
Safari: Cmd+Option+I > Toggle Device
```

### 2. Selecionar Dispositivo
```
iPhone SE (375x667) ← Recomendado
iPhone 12 Pro (390x844)
Samsung Galaxy S20 (360x800)
```

### 3. Testar URLs

#### Dashboard
```
http://localhost:5000/painel
```
**Verificar:**
- ✅ KPIs em 1 coluna vertical
- ✅ Filtros mês/ano empilhados
- ✅ Tabela "Necessidade de Compra" com scroll horizontal
- ✅ Gráficos adaptados

#### Financeiro
```
http://localhost:5000/financeiro
```
**Verificar:**
- ✅ Tabela com scroll horizontal
- ✅ Badges legíveis
- ✅ Botões "Ver" e "Lançar" clicáveis
- ✅ Valores em destaque

#### Comprovantes
```
http://localhost:5000/financeiro/comprovantes
```
**Verificar:**
- ✅ Cards de cliente não quebrados
- ✅ Tabela com scroll
- ✅ Botão "Ver" clicável
- ✅ Badges de método legíveis

#### Coletas
```
http://localhost:5000/coletas
```
**Verificar:**
- ✅ Lista de pedidos legível
- ✅ Botões "Ver" e "Coletar" clicáveis
- ✅ Status badges visíveis
- ✅ Tabelas com scroll

### 4. Testar Menu
```
1. Clique no ☰ (canto superior esquerdo)
2. Sidebar deve aparecer da esquerda
3. Overlay escuro deve cobrir a tela
4. Clique no overlay para fechar
```

---

## 📊 Checklist de Validação

| Item | Dashboard | Financeiro | Coletas |
|------|-----------|------------|---------|
| Viewport OK | ⬜ | ⬜ | ⬜ |
| Menu ☰ funciona | ⬜ | ⬜ | ⬜ |
| Tabelas scroll | ⬜ | ⬜ | ⬜ |
| Texto legível | ⬜ | ⬜ | ⬜ |
| Botões clicáveis | ⬜ | ⬜ | ⬜ |
| Layout 1 coluna | ⬜ | ⬜ | ⬜ |

---

## 🐛 Troubleshooting

### Problema: Menu não abre
```javascript
// Verificar no console:
console.log(document.querySelector('.sidebar'));
console.log(document.getElementById('menu-toggle'));
```

### Problema: Tabela sem scroll
```
- Verificar se há <div class="table-responsive"> envolvendo <table>
- Verificar no DevTools se min-width: 600px está aplicado
```

### Problema: Sidebar não aparece
```
- Verificar se sidebar.js está carregando
- Ver console para erros JavaScript
```

---

## ✅ Teste Completo

Marque todos os checkboxes acima e o sistema está 100% responsivo!

