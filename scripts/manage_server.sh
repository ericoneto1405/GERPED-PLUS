#!/bin/bash
# ==================================================================
# Script de Gerenciamento do Servidor Flask - Sistema GERPED
# ==================================================================
# Gerencia o ciclo de vida do servidor Flask de forma robusta
#
# Uso:
#   ./manage_server.sh start    - Inicia o servidor
#   ./manage_server.sh stop     - Para o servidor
#   ./manage_server.sh restart  - Reinicia o servidor
#   ./manage_server.sh status   - Mostra status do servidor
#   ./manage_server.sh logs     - Mostra logs em tempo real
#
# Autor: Sistema GERPED
# ==================================================================

set -euo pipefail

# Configurações
PORT=5004
PID_FILE="/tmp/flask_server.pid" # Usar /tmp para evitar poluir o projeto
LOG_FILE="instance/logs/server.log"
RUN_SCRIPT="run.py"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Resolve o binário do Python a ser usado
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python3" ]; then
    PYTHON_CMD="$VIRTUAL_ENV/bin/python3"
elif [ -x "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
else
    echo -e "${RED}❌ Python3 não encontrado. Crie o ambiente com 'python3 -m venv venv'.${NC}"
    exit 1
fi

# Utilitário para limpar PID inválido
cleanup_stale_pid() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ! ps -p "$PID" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
        fi
    fi
}

# Verifica dependências
command -v lsof >/dev/null 2>&1 || { echo -e "${RED}❌ Comando 'lsof' não encontrado. Por favor, instale-o.${NC}"; exit 1; }

# Funções auxiliares
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verifica se a porta está em uso
check_port() {
    lsof -ti TCP:"$PORT" 2>/dev/null || true
}

# Verifica se o servidor está rodando
is_running() {
    cleanup_stale_pid
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID file existe mas processo não está rodando
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Inicia o servidor
start_server() {
    print_info "Verificando servidor Flask..."
    
    # Verifica se já está rodando
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_warning "Servidor já está rodando (PID: $PID)"
        print_info "Use './manage_server.sh stop' para parar"
        return 1
    fi
    
    # Verifica se a porta está em uso por outro processo
    PORT_PIDS=$(check_port)
    if [ -n "$PORT_PIDS" ]; then
        print_warning "Porta $PORT está em uso pelos processos: $PORT_PIDS"
        print_info "Encerrando processos conflitantes..."
        echo "$PORT_PIDS" | xargs kill -9 2>/dev/null || true
        
        # Aguarda a porta ficar disponível (máximo 10 segundos)
        print_info "Aguardando porta $PORT ficar disponível..."
        for i in {1..10}; do
            sleep 1
            if [ -z "$(check_port)" ]; then
                print_success "Porta $PORT está disponível"
                break
            fi
            if [ $i -eq 10 ]; then
                print_error "Porta $PORT ainda está em uso após 10 segundos"
                return 1
            fi
        done
    fi
    
    # Cria diretório de logs se não existir
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Inicia o servidor
    print_info "Iniciando servidor Flask na porta $PORT..."
    nohup "$PYTHON_CMD" "$RUN_SCRIPT" > "$LOG_FILE" 2>&1 & SERVER_PID=$!
    
    # Salva o PID
    echo "$SERVER_PID" > "$PID_FILE"
    
    # Aguarda servidor iniciar
    sleep 3
    
    # Verifica se iniciou corretamente
    if ps -p "$SERVER_PID" > /dev/null 2>&1; then
        print_success "Servidor iniciado com sucesso!"
        print_info "PID: $SERVER_PID"
        print_info "Porta: $PORT"
        print_info "Logs: $LOG_FILE"
        print_info "URL: http://127.0.0.1:$PORT"
        echo
        print_info "Use 'make server-logs' para ver os logs em tempo real"
        print_info "Use 'make server-stop' para parar o servidor"
    else
        print_error "Falha ao iniciar o servidor"
        rm -f "$PID_FILE"
        print_info "Verifique os logs em: $LOG_FILE"
        return 1
    fi
}

# Para o servidor
stop_server() {
    cleanup_stale_pid
    print_info "Parando servidor Flask..."
    
    # Tenta parar pelo PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -15 "$PID" || true # Envia sinal de término gracioso
            sleep 2
            
            # Se ainda estiver rodando, força
            if ps -p "$PID" > /dev/null 2>&1; then
                print_warning "Processo não respondeu ao SIGTERM, forçando..."
                kill -9 "$PID" || true
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # Garante que todos os processos na porta foram encerrados
    PORT_PIDS=$(check_port)
    if [ -n "$PORT_PIDS" ]; then
        print_info "Encerrando processos residuais na porta $PORT..."
        kill -9 $PORT_PIDS || true
        sleep 1
    fi
    
    # Verifica se parou
    if [ -z "$(check_port)" ]; then
        print_success "Servidor parado com sucesso!"
    else
        print_error "Alguns processos ainda estão rodando na porta $PORT"
        return 1
    fi
}

# Reinicia o servidor
restart_server() {
    print_info "Reiniciando servidor Flask..."
    stop_server
    sleep 2
    start_server
}

# Mostra status do servidor
show_status() {
    cleanup_stale_pid
    echo
    print_info "====== Status do Servidor Flask ======"
    echo
    
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_success "Servidor está RODANDO"
        echo
        echo "  PID: $PID"
        echo "  Porta: $PORT"
        echo "  URL: http://127.0.0.1:$PORT"
        echo "  Log: $LOG_FILE"
        echo
        
        # Mostra informações do processo
        print_info "Informações do Processo:"
        ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,cmd | tail -n +2 | awk '{print "  "$0}'
        
        # Verifica se está respondendo
        if command -v curl > /dev/null 2>&1; then
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" || echo "000")
            if [ "$HTTP_STATUS" != "000" ]; then
                print_success "Servidor está respondendo (HTTP $HTTP_STATUS)"
            else
                print_warning "Servidor não está respondendo"
            fi
        fi
    else
        print_warning "Servidor está PARADO"
        echo
        
        # Verifica se há processos residuais na porta
        PORT_PIDS=$(check_port)
        if [ -n "$PORT_PIDS" ]; then
            print_warning "Processos residuais na porta $PORT:"
            echo "$PORT_PIDS" | while read pid; do
                ps -p "$pid" -o pid,cmd | tail -n +2 | awk '{print "  "$0}'
            done
            echo
            print_info "Use './manage_server.sh stop' para limpar"
        fi
    fi
    

    echo
}

# Mostra logs em tempo real
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_error "Arquivo de log não encontrado: $LOG_FILE"
        return 1
    fi
    
    print_info "Mostrando logs (Ctrl+C para sair)..."
    echo
    tail -f "$LOG_FILE"
}

# Menu principal
case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs}"
        echo
        echo "Comandos:"
        echo "  start    - Inicia o servidor Flask"
        echo "  stop     - Para o servidor Flask"
        echo "  restart  - Reinicia o servidor Flask"
        echo "  status   - Mostra status do servidor"
        echo "  logs     - Mostra logs em tempo real"
        exit 1
        ;;
esac
