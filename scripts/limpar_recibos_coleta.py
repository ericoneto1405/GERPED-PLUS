#!/usr/bin/env python3
"""
Remove arquivos de recibos de coleta que não estão mais referenciados no banco.

Uso:
  python scripts/limpar_recibos_coleta.py           # modo simulação (dry-run)
  python scripts/limpar_recibos_coleta.py --aplicar # remove de fato
"""
import argparse
import os
from pathlib import Path

from meu_app import create_app, db
from meu_app.models import Coleta


def _get_recibos_dir(app) -> Path:
    configured = os.getenv("COLETAS_RECIBO_DIR", "uploads/recibos_coleta")
    target_dir = Path(app.root_path).parent / configured
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def main():
    parser = argparse.ArgumentParser(description="Limpeza de recibos de coleta órfãos.")
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Aplica a limpeza. Sem este flag é apenas simulação.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        recibos_dir = _get_recibos_dir(app)
        arquivos = [p for p in recibos_dir.iterdir() if p.is_file()]

        referenciados = set()
        for coleta in Coleta.query.all():
            if coleta.recibo_documento:
                referenciados.add(Path(coleta.recibo_documento).name)
            if coleta.recibo_assinatura:
                referenciados.add(Path(coleta.recibo_assinatura).name)

        orfaos = [p for p in arquivos if p.name not in referenciados]

        print("Resumo da limpeza de recibos de coleta:")
        print(f"- Diretório: {recibos_dir}")
        print(f"- Arquivos encontrados: {len(arquivos)}")
        print(f"- Referenciados no banco: {len(referenciados)}")
        print(f"- Órfãos para remoção: {len(orfaos)}")

        if not orfaos:
            print("\nNenhum recibo órfão para remover.")
            return

        if not args.aplicar:
            print("\nModo simulação: nenhuma alteração foi aplicada.")
            print("Para aplicar, execute com --aplicar.")
            return

        removidos = 0
        for arquivo in orfaos:
            try:
                arquivo.unlink()
                removidos += 1
            except Exception as exc:
                print(f"Falha ao remover {arquivo}: {exc}")

        print(f"\nLimpeza concluída. Arquivos removidos: {removidos}.")


if __name__ == "__main__":
    main()
