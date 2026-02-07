"""
Inferência do classificador PyTorch treinado para validar comprovantes.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Dict, Optional

from flask import current_app

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - ambiente sem PyTorch
    torch = None
    nn = None

TOKEN_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)

LOGGER = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]


def _vectorize(tokens: list[str], vocab: Dict[str, int]) -> "torch.Tensor":
    vector = torch.zeros(len(vocab), dtype=torch.float32)
    for token in tokens:
        idx = vocab.get(token)
        if idx is not None:
            vector[idx] += 1.0
    return vector


if nn is not None:
    class _ValidatorNet(nn.Module):  # pragma: no cover - rede já testada em treinamento
        def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256):
            super().__init__()
            self.model = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(hidden_dim, num_classes),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.model(x)
else:  # pragma: no cover - ambiente sem PyTorch
    _ValidatorNet = None  # type: ignore[assignment]


class PaymentValidatorService:
    """
    Carrega modelo/vocabulário e executa inferência de forma lazy e thread-safe.
    """

    _lock = threading.Lock()
    _initialized = False
    _model: Optional["_ValidatorNet"] = None
    _vocab: Dict[str, int] = {}
    _label_to_idx: Dict[str, int] = {}
    _idx_to_label: Dict[int, str] = {}
    _backend_name = "pytorch_validator_v1"

    @classmethod
    def _get_model_directory(cls) -> Path:
        base_path = Path(current_app.root_path).parent
        from .config import FinanceiroConfig

        configured = current_app.config.get("PAYMENT_VALIDATOR_DIR")
        model_dir = Path(configured or FinanceiroConfig.PAYMENT_VALIDATOR_DIR)
        if not model_dir.is_absolute():
            model_dir = base_path / model_dir
        return model_dir

    @classmethod
    def _load_resources(cls) -> None:
        if cls._initialized:
            return

        if torch is None or nn is None:
            LOGGER.warning("PyTorch não está instalado; validador indisponível.")
            cls._initialized = True
            return

        with cls._lock:
            if cls._initialized:
                return

            model_dir = cls._get_model_directory()
            model_path = model_dir / "payment_validator.pt"
            vocab_path = model_dir / "vocab.json"
            labels_path = model_dir / "labels.json"

            try:
                if not model_path.exists() or not vocab_path.exists() or not labels_path.exists():
                    LOGGER.warning(
                        "Arquivos do modelo PyTorch não encontrados em %s", model_dir
                    )
                    cls._initialized = True
                    return

                with vocab_path.open("r", encoding="utf-8") as fh:
                    cls._vocab = json.load(fh)

                with labels_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    cls._label_to_idx = data.get("label_to_idx", {})
                    cls._idx_to_label = {idx: label for label, idx in cls._label_to_idx.items()}

                input_dim = len(cls._vocab)
                num_classes = len(cls._label_to_idx)
                if not input_dim or not num_classes:
                    LOGGER.warning("Vocabulário ou labels vazios; validador indisponível.")
                    cls._initialized = True
                    return

                model = _ValidatorNet(input_dim=input_dim, num_classes=num_classes)
                state_dict = torch.load(model_path, map_location="cpu")
                model.load_state_dict(state_dict)
                model.eval()
                cls._model = model
                LOGGER.info("Modelo PyTorch de validação carregado com sucesso.")
            except Exception as exc:  # pragma: no cover - falhas inesperadas
                LOGGER.exception("Falha ao carregar modelo PyTorch: %s", exc)
                cls._model = None
            finally:
                cls._initialized = True

    @classmethod
    def evaluate_text(cls, text: Optional[str]) -> Dict[str, Optional[object]]:
        """
        Executa inferência no texto OCR e retorna label, confiança e scores.
        """
        cls._load_resources()

        response = {
            "backend": cls._backend_name,
            "label": None,
            "confidence": None,
            "scores": {},
            "error": None,
        }

        if cls._model is None or torch is None:
            response["error"] = "Modelo PyTorch indisponível no ambiente atual."
            return response

        tokens = _tokenize(text or "")
        if not tokens:
            response["error"] = "Texto OCR vazio ou inválido."
            return response

        vector = _vectorize(tokens, cls._vocab)
        if vector.sum() == 0:
            response["error"] = "Nenhum token conhecido encontrado no texto."
            return response

        with torch.no_grad():
            logits = cls._model(vector.unsqueeze(0))
            probabilities = torch.softmax(logits, dim=1).squeeze(0)

        probs = probabilities.numpy().tolist()
        scores = {
            cls._idx_to_label[idx]: float(probs[idx])
            for idx in range(len(probs))
        }

        best_idx = int(probabilities.argmax().item())
        response.update(
            {
                "label": cls._idx_to_label.get(best_idx),
                "confidence": float(probabilities[best_idx]),
                "scores": scores,
            }
        )
        return response
