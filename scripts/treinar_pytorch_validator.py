"""
Script de treinamento para o classificador PyTorch de comprovantes.

Como usar (offline):
1) Prepare um dataset rotulado (CSV ou JSON):
   - CSV: colunas "texto","label"
   - JSON: lista de objetos com campos "texto" e "label"
   Labels esperadas (exemplo): "valido", "suspeito", "invalido".
2) Rode:
   python scripts/treinar_pytorch_validator.py \
       --input dados_comprovantes.csv \
       --output_dir models/pytorch_validator \
       --epochs 5 --batch_size 32 --val_split 0.2
3) Ao finalizar, serão gerados:
   - payment_validator.pt
   - vocab.json
   - labels.json
   - training_report.json (métricas, hiperparâmetros)
4) Publicação:
   - Substitua os arquivos em models/pytorch_validator/ (ou ajuste PAYMENT_VALIDATOR_DIR)
   - Reinicie a aplicação.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

TOKEN_PATTERN = r"\b\w+\b"


def tokenize(text: str) -> List[str]:
    import re

    return [t.lower() for t in re.findall(TOKEN_PATTERN, text or "")]


def build_vocab(texts: List[str], min_freq: int = 1) -> Dict[str, int]:
    from collections import Counter

    counter = Counter()
    for txt in texts:
        counter.update(tokenize(txt))
    vocab = {token: idx for idx, (token, freq) in enumerate(counter.items()) if freq >= min_freq}
    return vocab


def vectorize(text: str, vocab: Dict[str, int]) -> torch.Tensor:
    vec = torch.zeros(len(vocab), dtype=torch.float32)
    for token in tokenize(text):
        idx = vocab.get(token)
        if idx is not None:
            vec[idx] += 1.0
    return vec


class TextDataset(Dataset):
    def __init__(self, samples: List[Tuple[str, int]], vocab: Dict[str, int]):
        self.samples = samples
        self.vocab = vocab

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text, label = self.samples[idx]
        return vectorize(text, self.vocab), torch.tensor(label, dtype=torch.long)


class ValidatorNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.model(x)


@dataclass
class TrainResult:
    train_loss: float
    val_loss: float
    train_acc: float
    val_acc: float


def load_data(input_path: Path) -> List[Tuple[str, str]]:
    if input_path.suffix.lower() == ".csv":
        import csv

        rows = []
        with input_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append((row["texto"], row["label"]))
        return rows
    else:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [(item["texto"], item["label"]) for item in data]
        raise ValueError("Formato de input não suportado. Use CSV ou JSON (lista).")


def prepare_splits(
    rows: List[Tuple[str, str]], val_split: float, seed: int
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    random.seed(seed)
    random.shuffle(rows)
    n_val = int(len(rows) * val_split)
    val_rows = rows[:n_val]
    train_rows = rows[n_val:]
    return train_rows, val_rows


def train_model(
    train_ds: Dataset,
    val_ds: Dataset,
    input_dim: int,
    num_classes: int,
    epochs: int,
    batch_size: int,
    lr: float,
    device: str,
) -> Tuple[ValidatorNet, TrainResult]:
    model = ValidatorNet(input_dim=input_dim, num_classes=num_classes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    def run_epoch(loader, train: bool):
        if train:
            model.train()
        else:
            model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            if train:
                opt.zero_grad()
            with torch.set_grad_enabled(train):
                logits = model(xb)
                loss = criterion(logits, yb)
                if train:
                    loss.backward()
                    opt.step()
            total_loss += loss.item() * xb.size(0)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += xb.size(0)
        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        return avg_loss, acc

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    for _ in range(epochs):
        train_loss, train_acc = run_epoch(train_loader, train=True)
        val_loss, val_acc = run_epoch(val_loader, train=False)

    result = TrainResult(train_loss=train_loss, val_loss=val_loss, train_acc=train_acc, val_acc=val_acc)
    return model, result


def save_artifacts(
    model: ValidatorNet,
    vocab: Dict[str, int],
    labels: List[str],
    output_dir: Path,
    training: TrainResult,
    epochs: int,
    batch_size: int,
    lr: float,
    val_split: float,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.save(model.state_dict(), output_dir / "payment_validator.pt")
    (output_dir / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "labels.json").write_text(
        json.dumps({"label_to_idx": {lbl: idx for idx, lbl in enumerate(labels)}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = {
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": lr,
        "val_split": val_split,
        "train_loss": training.train_loss,
        "val_loss": training.val_loss,
        "train_accuracy": training.train_acc,
        "val_accuracy": training.val_acc,
    }
    (output_dir / "training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Treinar classificador PyTorch de comprovantes.")
    parser.add_argument("--input", required=True, help="Caminho do CSV/JSON com campos 'texto' e 'label'.")
    parser.add_argument("--output_dir", default="models/pytorch_validator", help="Diretório de saída para artefatos.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--min_freq", type=int, default=1, help="Frequência mínima para incluir token no vocabulário.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    rows = load_data(input_path)
    texts = [t for t, _ in rows]
    labels_raw = [lbl for _, lbl in rows]
    labels_sorted = sorted(set(labels_raw))
    label_to_idx = {lbl: idx for idx, lbl in enumerate(labels_sorted)}

    # Split train/val
    train_rows, val_rows = prepare_splits(rows, val_split=args.val_split, seed=args.seed)

    # Vocab
    vocab = build_vocab(texts, min_freq=args.min_freq)

    # Datasets
    train_samples = [(t, label_to_idx[lbl]) for t, lbl in train_rows]
    val_samples = [(t, label_to_idx[lbl]) for t, lbl in val_rows]

    train_ds = TextDataset(train_samples, vocab)
    val_ds = TextDataset(val_samples, vocab)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, result = train_model(
        train_ds=train_ds,
        val_ds=val_ds,
        input_dim=len(vocab),
        num_classes=len(labels_sorted),
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=device,
    )

    save_artifacts(
        model=model,
        vocab=vocab,
        labels=labels_sorted,
        output_dir=output_dir,
        training=result,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        val_split=args.val_split,
    )
    print(f"Treino concluído. Artefatos salvos em {output_dir}")


if __name__ == "__main__":
    main()
