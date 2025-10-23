# Modelo de planilha para importar pedidos

Use este guia para montar o arquivo CSV ou Excel antes de fazer o upload no modulo **Pedidos -> Importar**.

## Colunas obrigatorias

O arquivo deve conter as colunas abaixo (nomes em letras minusculas, sem acentos):

| coluna            | descricao                                                                                   | exemplo                               |
|-------------------|----------------------------------------------------------------------------------------------|---------------------------------------|
| cliente_nome      | Nome oficial do cliente exatamente como aparece em **Clientes → Listar**                    | CAIQUE ANDRADE NASCIMENTO             |
| cliente_fantasia* | (Opcional) Nome fantasia / apelido do cliente                                                | KAIQUE ITATIM                         |
| produto_nome      | Nome do produto exatamente como aparece em **Produtos → Listar**                            | SKOL LATA 350ML                       |
| quantidade        | Quantidade inteira vendida                                                                   | 120                                   |
| preco_venda       | Preco unitario de venda (use ponto como separador decimal)                                   | 32.50                                 |
| data              | Data do pedido (YYYY-MM-DD ou DD/MM/YYYY)                                                    | 2025-04-29                            |

\* Informe ao menos `cliente_nome` ou `cliente_fantasia`. Se os dois estiverem presentes, ambos serão considerados para localizar o cadastro.

**Importante**
- Cada linha representa um item. Linhas com o mesmo cliente (mesma data) sao combinadas em um unico pedido com varios itens.
- Utilize nome oficial, nome fantasia ou ambos exatamente como cadastrados (o sistema ignora maiusculas/minusculas e acentos, mas nomes duplicados geram alerta).
- Evite formulas ou celulas mescladas. Salve o arquivo final como CSV ou XLSX.

## Exemplo pronto (CSV)

```
cliente_nome,cliente_fantasia,produto_nome,quantidade,preco_venda,data
CAIQUE ANDRADE NASCIMENTO,KAIQUE ITATIM,SKOL LATA 350ML,286,31.00,2025-04-29
CAIQUE ANDRADE NASCIMENTO,KAIQUE ITATIM,BRAHMA CHOPP LATA 350 ML,286,32.00,29/04/2025
LUCIANO VIEIRA SILVA DE ARAUJO,LUCIANO MOURA,RED BULL ENERGY DRINK 250 ML,144,150.00,29/04/2025
```

No exemplo acima, o cliente oficial "CAIQUE ANDRADE NASCIMENTO" (fantasia "KAIQUE ITATIM") gera um pedido com dois itens, enquanto "LUCIANO VIEIRA SILVA DE ARAUJO" (fantasia "LUCIANO MOURA") gera outro pedido no mesmo arquivo.

## Checklist rapido antes do upload

- [ ] Copiei o nome oficial e, se necessário, o nome fantasia direto das telas de Clientes/Produtos.
- [ ] Usei ponto (.) como separador decimal no `preco_venda`.
- [ ] Conferi se todas as datas estao em um formato valido (YYYY-MM-DD ou DD/MM/YYYY).
- [ ] Exportei/salvei o arquivo como CSV, XLSX ou XLS antes de enviar.
