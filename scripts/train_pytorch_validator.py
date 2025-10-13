"""
Treina um classificador simples em PyTorch para validar comprovantes a partir do texto OCR.

Fluxo:
1. Lê o dataset gerado em data/comprovantes_dataset.jsonl.
2. Normaliza os rótulos:
   - status_observacao vazio/None -> 'valido'
   - 'inválido' -> 'invalido'
   - demais textos ficam como estão (ex.: 'suspeito').
3. Tokeniza o texto (lower + regex) e constrói um vocabulário bag-of-words.
4. Treina uma rede linear (BoW -> Linear -> ReLU -> Linear) com CrossEntropyLoss.
5. Salva artefatos em models/pytorch_validator/:
   - model.pt (state_dict)
   - vocab.json
   - labels.json
   - training_report.json

Uso:
    PYTHONPATH=. python3 scripts/train_pytorch_validator.py --epochs 50
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "data" / "comprovantes_dataset.jsonl"
OUTPUT_DIR = ROOT_DIR / "models" / "pytorch_validator"

TOKEN_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)


def normalize_label(label: str | None) -> str:
    if not label:
        return "valido"
    label = label.strip().lower()
    if label == "inválido":
        return "invalido"
    return label


def tokenize(text: str) -> List[str]:
    return [tok.lower() for tok in TOKEN_PATTERN.findall(text)]


@dataclass
class Sample:
    tokens: List[str]
    label: str


def load_samples(path: Path) -> List[Sample]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")

    samples: List[Sample] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            text = record.get("texto_ocr") or ""
            label = normalize_label(record.get("status_observacao"))
            tokens = tokenize(text)
            if not tokens:
                continue
            samples.append(Sample(tokens=tokens, label=label))
    if not samples:
        raise RuntimeError("Nenhum sample válido carregado (texto ou tokens vazios).")
    return samples


def build_vocab(samples: Sequence[Sample], max_size: int = 5000, min_freq: int = 1) -> Dict[str, int]:
    freq = Counter()
    for sample in samples:
        freq.update(sample.tokens)

    vocab_tokens = [
        token
        for token, count in freq.most_common()
        if count >= min_freq
    ][:max_size]

    vocab = {token: idx for idx, token in enumerate(vocab_tokens)}
    return vocab


def vectorize(tokens: Sequence[str], vocab: Dict[str, int]) -> torch.Tensor:
    vec = torch.zeros(len(vocab), dtype=torch.float32)
    for token in tokens:
        idx = vocab.get(token)
        if idx is not None:
            vec[idx] += 1.0
    return vec


class BoWDataset(Dataset):
    def __init__(self, samples: Sequence[Sample], vocab: Dict[str, int], label_to_idx: Dict[str, int]):
        self.features = torch.stack([vectorize(s.tokens, vocab) for s in samples])
        self.labels = torch.tensor([label_to_idx[s.label] for s in samples], dtype=torch.long)

    def __len__(self) -> int:
        return self.labels.shape[0]

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]


class ValidatorNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


def split_samples(samples: List[Sample], val_ratio: float, seed: int) -> Tuple[List[Sample], List[Sample]]:
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(len(samples), generator=g).tolist()
    split_idx = max(1, int(len(samples) * (1 - val_ratio)))
    train_samples = [samples[i] for i in perm[:split_idx]]
    val_samples = [samples[i] for i in perm[split_idx:]]
    return train_samples, val_samples


def compute_accuracy(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = torch.argmax(logits, dim=1)
    correct = (preds == targets).sum().item()
    return correct / targets.shape[0]


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int,
    lr: float,
) -> Dict[str, List[float]]:
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    model.to(device)

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_acc = 0.0
        total = 0

        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            batch_size = batch_y.shape[0]
            train_loss += loss.item() * batch_size
            train_acc += compute_accuracy(logits, batch_y) * batch_size
            total += batch_size

        train_loss /= total
        train_acc /= total

        model.eval()
        val_loss = 0.0
        val_acc = 0.0
        val_total = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)
                logits = model(batch_x)
                loss = criterion(logits, batch_y)

                batch_size = batch_y.shape[0]
                val_loss += loss.item() * batch_size
                val_acc += compute_accuracy(logits, batch_y) * batch_size
                val_total += batch_size

        if val_total > 0:
            val_loss /= val_total
            val_acc /= val_total
        else:
            val_loss = float("nan")
            val_acc = float("nan")

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        print(
            f"[{epoch:03d}/{epochs}] "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.3f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.3f}"
        )

    return history


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> Dict[str, float]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    total_acc = 0.0
    total = 0
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            logits = model(batch_x)
            loss = criterion(logits, batch_y)

            batch_size = batch_y.shape[0]
            total_loss += loss.item() * batch_size
            total_acc += compute_accuracy(logits, batch_y) * batch_size
            total += batch_size
    if total == 0:
        return {"loss": float("nan"), "accuracy": float("nan")}
    return {"loss": total_loss / total, "accuracy": total_acc / total}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Treina classificador PyTorch para comprovantes.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    samples = load_samples(DATASET_PATH)
    label_set = sorted({s.label for s in samples})
    label_to_idx = {label: idx for idx, label in enumerate(label_set)}

    print("Labels disponíveis:", label_to_idx)
    label_freq = Counter(s.label for s in samples)
    print("Distribuição de labels:", dict(label_freq))

    train_samples, val_samples = split_samples(samples, val_ratio=args.val_ratio, seed=args.seed)
    vocab = build_vocab(train_samples)
    print(f"Vocabulário com {len(vocab)} tokens.")

    train_dataset = BoWDataset(train_samples, vocab, label_to_idx)
    val_dataset = BoWDataset(val_samples, vocab, label_to_idx)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ValidatorNet(input_dim=len(vocab), num_classes=len(label_to_idx))

    history = train(model, train_loader, val_loader, device, epochs=args.epochs, lr=args.lr)
    val_metrics = evaluate(model, val_loader, device)
    print("Métricas de validação final:", val_metrics)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUTPUT_DIR / "payment_validator.pt")

    with (OUTPUT_DIR / "vocab.json").open("w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=2)

    with (OUTPUT_DIR / "labels.json").open("w", encoding="utf-8") as fh:
        json.dump({"label_to_idx": label_to_idx}, fh, ensure_ascii=False, indent=2)

    with (OUTPUT_DIR / "training_report.json").open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "epochs": args.epochs,
                "learning_rate": args.lr,
                "batch_size": args.batch_size,
                "val_ratio": args.val_ratio,
                "history": history,
                "val_metrics": val_metrics,
                "label_distribution": dict(label_freq),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Artefatos salvos em: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
