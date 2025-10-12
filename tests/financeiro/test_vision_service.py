import pytest

from meu_app.financeiro.vision_service import VisionOcrService


def test_find_amount_ignores_large_plain_numbers():
    texto = """
    Comprovante BB
    Pix Enviado
    Valor: R$ 3.300,00
    Informações adicionais
    ID: E00000000202510021939023026977590
    Documento: 0000000000100204
    """

    amount = VisionOcrService._find_amount_in_text(texto)

    assert amount is not None
    assert amount == pytest.approx(3300.0)


def test_find_transaction_id_prefers_pix_identifier():
    texto = """
    Informações adicionais
    Documento: 0000000000100204
    ID: E00000000202510021939023026977590
    """

    assert (
        VisionOcrService._find_transaction_id_in_text(texto)
        == "E00000000202510021939023026977590"
    )


def test_find_transaction_id_falls_back_to_document_number():
    texto = """
    Informações adicionais
    Documento: 0000000000100204
    """

    assert (
        VisionOcrService._find_transaction_id_in_text(texto)
        == "0000000000100204"
    )
