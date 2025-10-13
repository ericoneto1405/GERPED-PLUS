# Gerenciamento do Servidor Flask

## Comandos Disponíveis

O sistema SAP agora possui um gerenciador robusto de servidor que evita conflitos de porta e processos duplicados.

### Comandos Make (Recomendado)

```bash
# Iniciar o servidor
make server-start
make dev              # Alias para server-start

# Parar o servidor
make server-stop

# Reiniciar o servidor
make server-restart

# Ver status do servidor
make server-status

# Ver logs em tempo real
make server-logs      # Ctrl+C para sair
```

### Comandos Diretos

Você também pode usar o script diretamente:

```bash
# Iniciar
bash scripts/manage_server.sh start

# Parar
bash scripts/manage_server.sh stop

# Reiniciar
bash scripts/manage_server.sh restart

# Status
bash scripts/manage_server.sh status

# Logs
bash scripts/manage_server.sh logs
```

## Recursos

### 1. Detecção Automática de Conflitos

O sistema detecta automaticamente se a porta 5004 já está em uso antes de iniciar:

```bash
$ make server-start
ℹ️  Verificando servidor Flask...
⚠️  Porta 5004 está em uso pelos processos: 12345
ℹ️  Encerrando processos conflitantes...
✅ Servidor iniciado com sucesso!
```

### 2. Gerenciamento de PID

O servidor salva seu PID em `.flask.pid` para controle preciso:

```bash
$ cat .flask.pid
80555
```

### 3. Validação de Porta

Se você tentar rodar `python3 run.py` manualmente com a porta ocupada:

```bash
$ python3 run.py

❌ ERRO: Porta 5004 já está em uso!

Processo(s) usando a porta 5004:
  - PID: 80555

💡 Soluções:
  1. Use o gerenciador de servidor:
     make server-stop    # Para o servidor
     make server-start   # Inicia o servidor
     make server-status  # Verifica status

  2. Ou encerre manualmente:
     kill -9 80555
```

### 4. Limpeza Automática

O comando `stop` garante que todos os processos são encerrados:

```bash
$ make server-stop
ℹ️  Parando servidor Flask...
✅ Servidor parado com sucesso!
```

## Status Detalhado

O comando `status` mostra informações completas:

```bash
$ make server-status

ℹ️  ====== Status do Servidor Flask ======

✅ Servidor está RODANDO

  PID: 80555
  Porta: 5004
  URL: http://127.0.0.1:5004
  Log: instance/logs/server.log

ℹ️  Informações do Processo:
  80555     1   0.0  0.9   01:15

✅ Servidor está respondendo (HTTP 302)
```

## Logs

Os logs do servidor são salvos em `instance/logs/server.log`:

```bash
# Ver em tempo real
make server-logs

# Ver últimas linhas
tail -f instance/logs/server.log

# Buscar erros
grep -i error instance/logs/server.log
```

## Resolução de Problemas

### Porta ocupada por processo desconhecido

```bash
# Encontrar o processo
lsof -ti:5004

# Encerrar manualmente
lsof -ti:5004 | xargs kill -9

# Ou usar o gerenciador
make server-stop
```

### Servidor não inicia

1. Verifique os logs: `tail -50 instance/logs/server.log`
2. Verifique se há erros de sintaxe: `python3 -m py_compile run.py`
3. Verifique dependências: `pip3 install -r requirements.txt`

### Servidor não responde

```bash
# Verificar status
make server-status

# Reiniciar
make server-restart
```

## Arquivos Relacionados

- `scripts/manage_server.sh` - Script de gerenciamento
- `run.py` - Script principal do Flask com validações
- `.flask.pid` - Arquivo com PID do servidor (ignorado pelo git)
- `instance/logs/server.log` - Logs do servidor

## Fluxo de Trabalho Recomendado

### Desenvolvimento

```bash
# Iniciar o servidor
make dev

# Em outro terminal, ver logs
make server-logs

# Ao terminar
make server-stop
```

### Reiniciar após mudanças

```bash
# Reiniciar automaticamente
make server-restart
```

### Debug

```bash
# Ver status
make server-status

# Ver logs
make server-logs

# Se necessário, parar e iniciar
make server-stop
make server-start
```

## Diferenças da Versão Anterior

### Antes ❌

- Processos orphans em background
- Conflitos de porta frequentes
- Necessário `kill -9` manual
- Sem controle de PID
- Mensagens de erro confusas

### Agora ✅

- Gerenciamento automático de processos
- Detecção e resolução de conflitos
- Comandos simples (`make server-*`)
- Controle preciso via PID
- Mensagens claras e soluções sugeridas
- Logs centralizados
- Status detalhado

## Comandos Rápidos

```bash
# Setup inicial
make install

# Iniciar servidor
make dev

# Ver logs (outro terminal)
make server-logs

# Verificar tudo OK
make server-status

# Parar ao fim do dia
make server-stop
```

