import re
from typing import Union


class PrecoInvalidoError(ValueError):
    """Erro lançado quando o preço digitado é inválido."""


def normalizar_preco_brl(valor: Union[str, float, int], exigir_virgula: bool = True) -> float:
    """
    Converte strings no formato brasileiro (R$ 10,50) para float.
    Pode opcionalmente exigir a presença da vírgula para os centavos.
    """
    if valor is None:
        raise PrecoInvalidoError("Informe o valor do preço.")

    if isinstance(valor, (int, float)) and not exigir_virgula:
        return float(valor)

    valor_str = str(valor).strip()
    if not valor_str:
        raise PrecoInvalidoError("Informe o valor do preço.")

    valor_str = valor_str.replace('R$', '').replace('\xa0', '').strip()

    if exigir_virgula:
        if ',' not in valor_str:
            raise PrecoInvalidoError("Use vírgula para separar os centavos (ex.: 10,50).")
        parte_decimal = valor_str.split(',', 1)[1]
        if not parte_decimal or not re.search(r'\d', parte_decimal):
            raise PrecoInvalidoError("Informe os centavos após a vírgula (ex.: 10,50).")

    valor_permitido = re.sub(r'[^0-9,.-]', '', valor_str)
    valor_sem_milhar = valor_permitido.replace('.', '')
    valor_normalizado = valor_sem_milhar.replace(',', '.')

    try:
        return float(valor_normalizado)
    except ValueError:
        raise PrecoInvalidoError("Preço inválido. Use vírgula para separar os centavos.")
