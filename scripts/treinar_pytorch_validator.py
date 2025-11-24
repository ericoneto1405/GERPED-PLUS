"""Ferramenta de treinamento para o validador PyTorch de comprovantes.

Uso básico:

    python scripts/treinar_pytorch_validator.py \
        --dataset data/financeiro/comprovantes_rotulados.csv \
        --output-dir instance/payment_validator \
        --epochs 10

O CSV de entrada deve conter as colunas `texto` (conteúdo OCR) e `label`
(classe desejada, ex.: valido, suspeito, invalido). O script monta o
vocabulário, treina a mesma rede utilizada em produção e salva:

- payment_validator.pt
- vocab.json
- labels.json

Requer PyTorch instalado.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

from meu_app.financeiro.pytorch_validator import _tokenize, _ValidatorNet


def build_vocab(
    records: List[Tuple[str, str]], min_freq: int
) -> Dict[str, int]:
    counter = Counter()
    for text, _ in records:
        counter.update(_tokenize(text))
    vocab = {
        token: idx
        for idx, (token, freq) in enumerate(counter.items())
        if freq >= min_freq
    }
    if not vocab:
        raise ValueError(
            "Vocabulário resultante ficou vazio; reduza min_freq ou adicione mais dados."
        )
    return vocab


def build_label_mapping(records: List[Tuple[str, str]]) -> Dict[str, int]:
    labels = sorted({label for _, label in records})
    if len(labels) < 2:
        raise ValueError("São necessárias pelo menos duas classes para treinamento.")
    return {label: idx for idx, label in enumerate(labels)}


def vectorize(text: str, vocab: Dict[str, int]) -> torch.Tensor:
    vector = torch.zeros(len(vocab), dtype=torch.float32)
    for token in _tokenize(text):
        idx = vocab.get(token)
        if idx is not None:
            vector[idx] += 1.0
    return vector


class PaymentDataset(Dataset):
    def __init__(
        self,
        records: List[Tuple[str, str]],
        vocab: Dict[str, int],
        label_to_idx: Dict[str, int],
    ):
        self.records = records
        self.vocab = vocab
        self.label_to_idx = label_to_idx

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        text, label = self.records[idx]
        return (
            vectorize(text, self.vocab),
            torch.tensor(self.label_to_idx[label], dtype=torch.long),
        )


def load_dataset(path: Path) -> List[Tuple[str, str]]:
    records: List[Tuple[str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if "texto" not in reader.fieldnames or "label" not in reader.fieldnames:
            raise ValueError("CSV precisa ter as colunas 'texto' e 'label'.")
        for row in reader:
            texto = (row.get("texto") or "").strip()
            label = (row.get("label") or "").strip()
            if not texto or not label:
                continue
            records.append((texto, label))
    if not records:
        raise ValueError("Nenhum registro válido encontrado no dataset.")
    return records


def split_dataset(dataset: Dataset, val_split: float):
    if not 0 < val_split < 1:
        raise ValueError("val_split deve estar entre 0 e 1.")
    val_size = max(1, int(len(dataset) * val_split))
    train_size = len(dataset) - val_size
    return random_split(dataset, [train_size, val_size])


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    device: torch.device,
):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * inputs.size(0)

        avg_loss = total_loss / len(train_loader.dataset)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        print(
            f"Epoch {epoch}/{epochs} | Loss: {avg_loss:.4f} "
            f"| ValLoss: {val_loss:.4f} | ValAcc: {val_acc:.4f}"
        )


def evaluate(model: nn.Module, loader: DataLoader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            total_loss += loss.item() * inputs.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == labels).sum().item()
    avg_loss = total_loss / len(loader.dataset)
    accuracy = correct / len(loader.dataset)
    return avg_loss, accuracy


def save_artifacts(
    output_dir: Path,
    model: nn.Module,
    vocab: Dict[str, int],
    label_to_idx: Dict[str, int],
):
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_dir / "payment_validator.pt")
    with (output_dir / "vocab.json").open("w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=2)
    with (output_dir / "labels.json").open("w", encoding="utf-8") as fh:
        json.dump({"label_to_idx": label_to_idx}, fh, ensure_ascii=False, indent=2)
    print(f"Artefatos salvos em {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Treina o validador PyTorch de comprovantes."
    )
    parser.add_argument("--dataset", required=True, type=Path, help="CSV texto,label.")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Diretório para salvar modelo/vocab/labels.",
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--min-freq", type=int, default=2)
    parser.add_argument("--hidden-dim", type=int, default=256)
    return parser.parse_args()


def main():
    args = parse_args()
    records = load_dataset(args.dataset)
    vocab = build_vocab(records, min_freq=args.min_freq)
    label_to_idx = build_label_mapping(records)
    dataset = PaymentDataset(records, vocab, label_to_idx)
    train_ds, val_ds = split_dataset(dataset, args.val_split)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _ValidatorNet(
        input_dim=len(vocab),
        num_classes=len(label_to_idx),
        hidden_dim=args.hidden_dim,
    ).to(device)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    start = time.time()
    train(
        model,
        train_loader,
        val_loader,
        epochs=args.epochs,
        lr=args.lr,
        device=device,
    )
    elapsed = time.time() - start
    print(f"Treinamento concluído em {elapsed/60:.2f} minutos.")

    save_artifacts(args.output_dir, model.cpu(), vocab, label_to_idx)


if __name__ == "__main__":
    main()
