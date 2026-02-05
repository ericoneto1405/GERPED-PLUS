"""
Serviço para geração de recibo de coleta em imagem (JPG)
"""
from __future__ import annotations
import os
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from flask import current_app

from meu_app.exceptions import ConfigurationError, FileProcessingError
from meu_app.time_utils import local_now, to_local, now_utc

try:  # pragma: no cover - Pillow pode estar ausente em ambientes limitados
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
    PIL_IMPORT_ERROR: Optional[ImportError] = None
except ImportError as import_error:  # pragma: no cover
    Image = ImageDraw = ImageFont = None  # type: ignore
    PIL_AVAILABLE = False
    PIL_IMPORT_ERROR = import_error

FONT_CANDIDATES = [
    ("/System/Library/Fonts/SFNSDisplay.ttf", "/System/Library/Fonts/SFNSDisplay-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


class ReceiptService:
    """Serviço para geração de recibos de coleta."""

    _font_cache: Dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        cache_key = (size, bold)
        if cache_key in ReceiptService._font_cache:
            return ReceiptService._font_cache[cache_key]

        candidates = FONT_CANDIDATES or [(None, None)]
        for regular_path, bold_path in candidates:
            path = bold_path if bold else regular_path
            if path and os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size=size)
                    ReceiptService._font_cache[cache_key] = font
                    return font
                except OSError:
                    continue

        font = ImageFont.load_default()
        ReceiptService._font_cache[cache_key] = font
        return font

    @staticmethod
    def _draw_dashed_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, dash_length: int = 18,
                               gap: int = 12, color=(120, 120, 120), width: int = 3) -> None:
        x1, y1, x2, y2 = box

        def _draw_segment(start, end):
            draw.line([start, end], fill=color, width=width)

        # Top and bottom
        for x in range(x1, x2, dash_length + gap):
            _draw_segment((x, y1), (min(x + dash_length, x2), y1))
            _draw_segment((x, y2), (min(x + dash_length, x2), y2))

        # Left and right
        for y in range(y1, y2, dash_length + gap):
            _draw_segment((x1, y), (x1, min(y + dash_length, y2)))
            _draw_segment((x2, y), (x2, min(y + dash_length, y2)))

    @staticmethod
    def _format_data_coleta(valor) -> str:
        if isinstance(valor, datetime):
            return to_local(valor).strftime('%d/%m/%Y %H:%M')
        if valor:
            return str(valor)
        return local_now().strftime('%d/%m/%Y %H:%M')

    @staticmethod
    def gerar_recibo_imagem(coleta_data: Dict, output_dir: Optional[str] = None) -> str:
        """Gera um recibo em JPG baseado no layout fornecido."""
        if not PIL_AVAILABLE:
            erro = PIL_IMPORT_ERROR or ImportError('Biblioteca Pillow indisponível')
            raise ConfigurationError(
                message='Biblioteca Pillow não está instalada. Configure antes de gerar recibos.',
                details={'missing_dependency': 'Pillow', 'original_error': str(erro)}
            )

        receipts_dir = output_dir or os.path.join(current_app.instance_path, 'recibos')
        os.makedirs(receipts_dir, exist_ok=True)
        ReceiptService.limpar_recibos_antigos(receipts_dir)

        scale = current_app.config.get('COLETAS_RECIBO_SCALE', 2.0)
        try:
            scale = float(scale)
        except (TypeError, ValueError):
            scale = 2.0
        if scale <= 0:
            scale = 1.0

        dpi_value = max(72, int(round(150 * scale)))

        def s(value: int) -> int:
            return max(1, int(round(value * scale)))

        def cm(value: float) -> int:
            return max(1, int(round((dpi_value / 2.54) * value)))

        width, height = s(1240), s(1754)  # Aproximadamente A4 em 150 DPI
        margin = s(60)
        background_color = (255, 255, 255)
        accent = (31, 41, 55)  # azul escuro
        table_border = (15, 23, 42)

        title_font = ReceiptService._load_font(s(48), bold=True)
        section_font = ReceiptService._load_font(s(28), bold=True)
        text_font = ReceiptService._load_font(s(26))
        small_font = ReceiptService._load_font(s(22))
        tiny_font = ReceiptService._load_font(s(18))
        disclaimer_font = ReceiptService._load_font(max(1, int(round(title_font.size / 2))))
        header_title_font = ReceiptService._load_font(s(42), bold=True)
        header_label_font = ReceiptService._load_font(s(24), bold=True)
        header_value_font = ReceiptService._load_font(s(22))

        border_width = s(3)
        row_border_width = s(2)

        image = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(image)

        def _text_width(text: str, font: ImageFont.ImageFont) -> int:
            if hasattr(draw, "textlength"):
                return int(draw.textlength(text, font=font))
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]

        def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
            words = text.split()
            if not words:
                return []
            lines = []
            current = ''
            for word in words:
                candidate = f"{current} {word}".strip()
                if _text_width(candidate, font) <= max_width or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines

        y = margin
        draw.text((margin, y), 'Recibo de Coleta', font=header_title_font, fill=accent)
        y += header_title_font.size + s(14)

        info_columns = [
            ('PEDIDO', f"#{coleta_data.get('pedido_id', 'N/A')}"),
            ('CLIENTE', coleta_data.get('cliente_nome', 'N/A')),
            ('DATA DA COLETA', ReceiptService._format_data_coleta(coleta_data.get('data_coleta'))),
            ('COLETADO POR', coleta_data.get('nome_retirada', 'N/A')),
            ('CONFERIDO POR', coleta_data.get('nome_conferente', 'N/A')),
        ]

        table_x1 = margin
        table_x2 = width - margin
        table_width = table_x2 - table_x1
        col_weights = [0.12, 0.28, 0.2, 0.2, 0.2]
        col_widths = [int(table_width * w) for w in col_weights]
        col_widths[-1] = table_width - sum(col_widths[:-1])

        cell_padding_x = s(10)
        cell_padding_y = s(8)
        header_row_height = max(header_label_font.size + s(16), s(44))
        value_lines = [
            _wrap_text(str(value or 'N/A'), header_value_font, col_widths[idx] - cell_padding_x * 2)
            for idx, (_, value) in enumerate(info_columns)
        ]
        line_height = header_value_font.size + s(4)
        value_row_height = max(1, max(len(lines) for lines in value_lines)) * line_height + cell_padding_y * 2

        table_y1 = y
        table_y2 = y + header_row_height + value_row_height

        draw.rectangle([table_x1, table_y1, table_x2, table_y1 + header_row_height],
                       fill=(239, 241, 245), outline=table_border, width=border_width)
        draw.rectangle([table_x1, table_y1 + header_row_height, table_x2, table_y2],
                       fill=(255, 255, 255), outline=table_border, width=border_width)

        col_x = table_x1
        for idx, (label, _) in enumerate(info_columns):
            col_width = col_widths[idx]
            if idx > 0:
                draw.line([(col_x, table_y1), (col_x, table_y2)], fill=table_border, width=border_width)

            label_width = _text_width(label, header_label_font)
            if label_width + cell_padding_x * 2 <= col_width:
                label_x = col_x + (col_width - label_width) / 2
            else:
                label_x = col_x + cell_padding_x
            label_y = table_y1 + (header_row_height - header_label_font.size) / 2
            draw.text((label_x, label_y), label, font=header_label_font, fill=accent)

            value_y = table_y1 + header_row_height + cell_padding_y
            lines = value_lines[idx] or ['N/A']
            for line_idx, line in enumerate(lines):
                draw.text((col_x + cell_padding_x, value_y + line_idx * line_height),
                          line, font=header_value_font, fill=(60, 60, 60))

            col_x += col_width

        y = table_y2 + s(14)

        # Tabela de itens
        table_x1 = margin
        table_x2 = width - margin
        header_height = s(70)
        row_height = s(70)
        items = coleta_data.get('itens_coleta') or [{'produto_nome': 'Produto não informado', 'quantidade': '0'}]
        table_height = header_height + row_height * len(items)
        table_y1 = y
        table_y2 = y + table_height

        draw.rectangle([table_x1, table_y1, table_x2, table_y1 + header_height], fill=(239, 241, 245), outline=table_border,
                       width=border_width)
        draw.line([(table_x1 + (table_x2 - table_x1) * 0.65, table_y1),
                   (table_x1 + (table_x2 - table_x1) * 0.65, table_y1 + header_height)], fill=table_border, width=border_width)
        draw.text((table_x1 + s(20), table_y1 + header_height / 2 - section_font.size / 2), 'Produto', font=section_font,
                  fill=table_border)
        draw.text((table_x1 + (table_x2 - table_x1) * 0.65 + s(20),
                   table_y1 + header_height / 2 - section_font.size / 2), 'Quantidade Coletada', font=section_font,
                  fill=table_border)

        current_y = table_y1 + header_height
        for item in items:
            draw.rectangle([table_x1, current_y, table_x2, current_y + row_height], outline=table_border, width=row_border_width)
            produto = item.get('produto_nome', 'N/A')
            quantidade = str(item.get('quantidade', 0))
            produto_lines = textwrap.wrap(produto, width=40) or ['N/A']
            produto_text = '\n'.join(produto_lines)
            draw.multiline_text((table_x1 + s(20), current_y + s(15)), produto_text, font=small_font,
                                 fill=(50, 50, 50), spacing=s(4))
            draw.text((table_x1 + (table_x2 - table_x1) * 0.65 + s(20), current_y + s(20)), quantidade, font=small_font,
                      fill=(50, 50, 50))
            current_y += row_height

        y = table_y2 + cm(1.5)

        # Assinaturas
        line_length = (table_x2 - table_x1 - s(80)) / 2
        sig_y = y
        left_start = table_x1
        right_start = table_x1 + line_length + s(80)
        draw.line([(left_start, sig_y), (left_start + line_length, sig_y)], fill=table_border, width=border_width)
        draw.line([(right_start, sig_y), (right_start + line_length, sig_y)], fill=table_border, width=border_width)

        coletador_nome = coleta_data.get('nome_retirada') or 'N/A'
        conferente_nome = coleta_data.get('nome_conferente') or 'N/A'

        cpf_coletador = coleta_data.get('documento_retirada', 'N/A')
        cpf_conferente = coleta_data.get('cpf_conferente', 'N/A')

        draw.text((left_start, sig_y + s(10)), 'COLETADOR', font=small_font, fill=accent)
        draw.text((left_start, sig_y + s(45)), coletador_nome, font=tiny_font, fill=(70, 70, 70))
        draw.text((left_start, sig_y + s(70)), f"CPF: {cpf_coletador}", font=tiny_font, fill=(90, 90, 90))
        draw.text((right_start, sig_y + s(10)), 'CONFERENTE', font=small_font, fill=accent)
        draw.text((right_start, sig_y + s(45)), conferente_nome, font=tiny_font, fill=(70, 70, 70))
        draw.text((right_start, sig_y + s(70)), f"CPF: {cpf_conferente}", font=tiny_font, fill=(90, 90, 90))

        disclaimer_text = (
            "Ao assinar, fica confirmado a conferência do recibo. Não serão aceitas reclamações posteriores."
        )
        disclaimer_lines = _wrap_text(disclaimer_text, disclaimer_font, int(line_length))
        disclaimer_y = sig_y + s(95)
        if disclaimer_lines:
            draw.multiline_text(
                (left_start, disclaimer_y),
                "\n".join(disclaimer_lines),
                font=disclaimer_font,
                fill=(80, 80, 80),
                spacing=s(6),
            )
        line_height = disclaimer_font.size + s(6)
        disclaimer_height = line_height * max(1, len(disclaimer_lines))
        sig_block_bottom = sig_y + s(150)
        y = max(sig_block_bottom, disclaimer_y + disclaimer_height + s(20))

        placeholder_height = cm(6.0)
        placeholder_box = (table_x1, y, table_x2, y + placeholder_height)
        ReceiptService._draw_dashed_rectangle(
            draw,
            placeholder_box,
            dash_length=s(18),
            gap=s(12),
            width=border_width,
        )
        msg = 'DOCUMENTO DE IDENTIFICAÇÃO\nAUTORIZADO PARA COLETA'
        bbox = draw.multiline_textbbox((0, 0), msg, font=small_font, align='center')
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.multiline_text(
            ((table_x1 + table_x2 - text_width) / 2, y + (placeholder_height - text_height) / 2),
            msg,
            font=small_font,
            fill=(90, 90, 90),
            align='center'
        )

        y += placeholder_height + s(60)
        rodape = f"Recibo emitido em {local_now().strftime('%d/%m/%Y às %H:%M:%S')} pelo Sistema GERPED"
        draw.text((margin, y), rodape, font=tiny_font, fill=(120, 120, 120))

        timestamp = local_now().strftime('%Y%m%d_%H%M%S')
        filename = f"recibo_coleta_{coleta_data.get('pedido_id', 'N')}_{timestamp}.jpg"
        filepath = os.path.join(receipts_dir, filename)

        try:
            image.save(filepath, format='JPEG', quality=90, dpi=(dpi_value, dpi_value))
        except Exception as exc:  # pragma: no cover - exceções raras
            raise FileProcessingError(
                message='Falha ao salvar recibo de coleta em JPG',
                details={'pedido_id': coleta_data.get('pedido_id'), 'arquivo': filepath, 'error': str(exc)}
            ) from exc

        current_app.logger.info(
            'Recibo de coleta (JPG) gerado com sucesso',
            extra={'pedido_id': coleta_data.get('pedido_id'), 'arquivo': filepath,
                   'quantidade_itens': len(coleta_data.get('itens_coleta', []))},
        )
        return filepath

    @staticmethod
    def gerar_recibo_pdf(coleta_data: Dict, output_dir: Optional[str] = None) -> str:
        """Gera recibo em PDF (a partir da imagem) e retorna o caminho."""
        image_path = ReceiptService.gerar_recibo_imagem(coleta_data, output_dir=output_dir)
        pdf_path = str(Path(image_path).with_suffix('.pdf'))

        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(pdf_path, format='PDF')
        except Exception as exc:  # pragma: no cover - exceções raras
            raise FileProcessingError(
                message='Falha ao salvar recibo de coleta em PDF',
                details={'pedido_id': coleta_data.get('pedido_id'), 'arquivo': pdf_path, 'error': str(exc)}
            ) from exc

        current_app.logger.info(
            'Recibo de coleta (PDF) gerado com sucesso',
            extra={'pedido_id': coleta_data.get('pedido_id'), 'arquivo': pdf_path,
                   'quantidade_itens': len(coleta_data.get('itens_coleta', []))},
        )
        return pdf_path

    @staticmethod
    def enfileirar_recibo_imagem(coleta_data: Dict) -> Optional[str]:
        """Tenta enfileirar a geração do recibo em imagem."""
        try:
            from meu_app.queue import enqueue_pdf_job
        except ImportError as exc:  # pragma: no cover
            current_app.logger.error('Erro ao importar fila para geração de recibo', exc_info=exc)
            return None

        try:
            job_id = enqueue_pdf_job(coleta_data)
            if job_id:
                ReceiptService.agendar_limpeza_recibos()
            return job_id
        except Exception as exc:  # pragma: no cover
            current_app.logger.warning(
                'Falha ao enfileirar geração assíncrona de recibo. Utilizando fluxo síncrono.',
                exc_info=exc,
                extra={'pedido_id': coleta_data.get('pedido_id')},
            )
            return None

    @staticmethod
    def enfileirar_recibo_pdf(coleta_data: Dict) -> Optional[str]:
        """Compatibilidade retroativa."""
        return ReceiptService.enfileirar_recibo_imagem(coleta_data)

    @staticmethod
    def limpar_recibos_antigos(output_dir: Optional[str] = None, ttl_hours: Optional[int] = None) -> int:
        """Remove recibos antigos com base na configuração de TTL."""
        ttl = ttl_hours or current_app.config.get('COLETAS_RECIBO_TTL_HORAS', 24)
        if ttl <= 0:
            return 0

        diretorio = Path(output_dir or os.path.join(current_app.instance_path, 'recibos'))
        if not diretorio.exists():
            return 0

        limite_temporal = now_utc() - timedelta(hours=ttl)
        removidos = 0

        for arquivo in diretorio.glob('recibo_coleta_*'):
            if arquivo.suffix.lower() not in {'.jpg', '.jpeg', '.pdf'}:
                continue
            try:
                mod_time = datetime.fromtimestamp(arquivo.stat().st_mtime, timezone.utc)
                if mod_time < limite_temporal:
                    arquivo.unlink()
                    removidos += 1
            except FileNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover
                current_app.logger.warning(
                    'Falha ao remover recibo expirado',
                    exc_info=exc,
                    extra={'arquivo': str(arquivo)},
                )

        if removidos:
            current_app.logger.info(
                'Recibos de coleta expirados removidos',
                extra={'removidos': removidos, 'diretorio': str(diretorio)},
            )

        return removidos

    @staticmethod
    def agendar_limpeza_recibos(ttl_hours: Optional[int] = None) -> Optional[str]:
        """Enfileira uma tarefa para limpar recibos expirados."""
        try:
            from meu_app.queue import enqueue_receipt_cleanup_job
        except ImportError as exc:  # pragma: no cover
            current_app.logger.debug('Fila indisponível para limpeza de recibos', exc_info=exc)
            return None

        try:
            return enqueue_receipt_cleanup_job(ttl_hours=ttl_hours)
        except Exception as exc:  # pragma: no cover
            current_app.logger.debug('Não foi possível agendar limpeza de recibos expirados', exc_info=exc)
            return None
