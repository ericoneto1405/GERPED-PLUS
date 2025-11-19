#!/usr/bin/env python3
"""
Monitoramento ativo básico para o go-live do Sistema GERPED.

Coleta métricas de CPU, memória e latência HTTP do endpoint informado
e grava em stdout e/ou arquivo JSONL.

Dependências opcionais:
    - psutil (para métricas mais precisas de CPU/RAM)

Uso:
    python scripts/monitoring_agent.py --target-url http://localhost:5000/healthz \
        --interval 60 --output /var/log/sap/monitoring.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - import opcional
    psutil = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agente simples de monitoramento ativo para go-live.")
    parser.add_argument("--target-url", required=True, help="Endpoint para medir tempo de resposta (ex: http://localhost:5000/healthz)")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo em segundos entre coletas (padrão: 60)")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout em segundos para requisição HTTP (padrão: 5)")
    parser.add_argument("--output", help="Arquivo JSONL para persistir métricas (opcional)")
    parser.add_argument("--samples", type=int, default=0, help="Quantidade de amostras antes de encerrar (0 = roda infinito)")
    return parser.parse_args()


def collect_system_metrics() -> Dict[str, Any]:
    """Coleta CPU e memória usando psutil se disponível."""
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None

    if psutil:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram_percent = psutil.virtual_memory().percent
    else:  # Fallback utilizando load average
        try:
            load1, _, _ = os.getloadavg()
            cores = os.cpu_count() or 1
            cpu_percent = round((load1 / cores) * 100, 2)
        except (OSError, ValueError):
            cpu_percent = None

        try:
            with open("/proc/meminfo", encoding="utf-8") as meminfo:
                info = {line.split(":")[0]: float(line.split(":")[1].strip().split()[0]) for line in meminfo}
            mem_total = info.get("MemTotal")
            mem_available = info.get("MemAvailable")
            if mem_total and mem_available:
                ram_percent = round(100 - ((mem_available / mem_total) * 100), 2)
        except FileNotFoundError:
            ram_percent = None

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
    }


def measure_http_latency(url: str, timeout: int) -> Dict[str, Any]:
    """Executa uma requisição GET e retorna status/latência."""
    start = time.perf_counter()
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status_code": response.status,
                "latency_ms": latency_ms,
                "error": None,
            }
    except urllib.error.URLError as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


def write_output(payload: Dict[str, Any], output_path: Optional[str]) -> None:
    """Grava métrica em stdout e, opcionalmente, em arquivo JSONL."""
    line = json.dumps(payload, ensure_ascii=False)
    print(line)
    sys.stdout.flush()

    if output_path:
        with open(output_path, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")


def main() -> None:
    args = parse_args()
    sample_count = 0

    if args.output:
        output_dir = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(output_dir, exist_ok=True)

    while True:
        timestamp = datetime.utcnow().isoformat()
        system_metrics = collect_system_metrics()
        http_metrics = measure_http_latency(args.target_url, args.timeout)

        payload = {
            "timestamp": timestamp,
            "target_url": args.target_url,
            "system": system_metrics,
            "http": http_metrics,
        }

        write_output(payload, args.output)

        sample_count += 1
        if args.samples and sample_count >= args.samples:
            break

        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
