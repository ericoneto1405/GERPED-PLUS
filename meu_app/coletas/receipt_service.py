"""
Serviço para geração de recibo de coleta em PDF
Modelo EXATO baseado na interface mostrada
"""
from datetime import datetime
import os
from typing import Dict, Optional

from flask import current_app

from meu_app.exceptions import ConfigurationError, FileProcessingError

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Rect, Line
    from reportlab.graphics import renderPDF

    REPORTLAB_AVAILABLE = True
    REPORTLAB_IMPORT_ERROR: Optional[ImportError] = None
except ImportError as import_error:  # pragma: no cover - ambiente sem reportlab
    REPORTLAB_AVAILABLE = False
    REPORTLAB_IMPORT_ERROR = import_error


class ReceiptService:
    """Serviço para geração de recibos de coleta"""
    
    @staticmethod
    def gerar_recibo_pdf(coleta_data: Dict, output_dir: Optional[str] = None) -> str:
        """
        Gera um recibo PDF EXATO como o modelo mostrado
        
        Args:
            coleta_data: Dicionário com dados da coleta
            output_dir: Diretório opcional para salvar o PDF (default: instance/recibos)
            
        Returns:
            str: Caminho do arquivo PDF gerado
        """
        if not REPORTLAB_AVAILABLE:
            erro = REPORTLAB_IMPORT_ERROR or ImportError("Biblioteca reportlab indisponível")
            current_app.logger.error(
                "Dependência ReportLab ausente ao gerar recibo de coleta",
                exc_info=erro,
            )
            raise ConfigurationError(
                message="Biblioteca ReportLab não está instalada. Configure dependência antes de gerar recibos.",
                details={"missing_dependency": "reportlab", "original_error": str(erro)},
            )
        
        receipts_dir = output_dir or os.path.join(current_app.instance_path, 'recibos')
        filepath = None
        
        try:
            # Criar diretório de recibos se não existir
            os.makedirs(receipts_dir, exist_ok=True)
            
            # Nome do arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recibo_coleta_{coleta_data['pedido_id']}_{timestamp}.pdf"
            filepath = os.path.join(receipts_dir, filename)
            
            # Criar documento PDF
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Estilos
            styles = getSampleStyleSheet()
            
            # Estilo para título principal "Recibo de Coleta"
            main_title_style = ParagraphStyle(
                'MainTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica-Bold'
            )
            
            # Estilo para informações do pedido
            info_style = ParagraphStyle(
                'OrderInfo',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.black,
                spaceAfter=8,
                fontName='Helvetica'
            )
            
            # Estilo para cabeçalho da tabela
            table_header_style = ParagraphStyle(
                'TableHeader',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            )
            
            # Estilo para assinaturas
            signature_style = ParagraphStyle(
                'SignatureStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=15,
                fontName='Helvetica-Bold'
            )
            
            # Estilo para documento de identificação
            doc_style = ParagraphStyle(
                'DocStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            )
            
            # Lista de elementos para o PDF
            story = []
            
            # Título principal "Recibo de Coleta"
            story.append(Paragraph("📄 Recibo de Coleta", main_title_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Informações do pedido e coleta
            pedido_info = f"""
            <b>Pedido:</b> #{coleta_data['pedido_id']}<br/>
            <b>Cliente:</b> {coleta_data.get('cliente_nome', 'N/A')}<br/>
            <b>Data da Coleta:</b> {coleta_data.get('data_coleta', datetime.now().strftime('%d/%m/%Y %H:%M'))}<br/>
            <b>Coletado por:</b> {coleta_data.get('nome_retirada', 'N/A')}<br/>
            <b>Liberado por:</b> {coleta_data.get('nome_conferente', 'N/A')}
            """
            story.append(Paragraph(pedido_info, info_style))
            story.append(Spacer(1, 0.5*cm))
            
            # Cabeçalho da tabela de itens
            story.append(Paragraph("Itens Coletados", table_header_style))
            
            # Criar tabela de itens coletados
            items_data = [['Produto', 'Quantidade Coletada']]
            
            for item in coleta_data.get('itens_coleta', []):
                produto_nome = item.get('produto_nome', 'N/A')
                quantidade = item.get('quantidade', 0)
                
                items_data.append([
                    produto_nome,
                    str(quantidade)
                ])
            
            # Tabela de itens
            items_table = Table(items_data, colWidths=[12*cm, 4*cm])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 0.5*cm))
            
            # ========================================
            # SEÇÃO DE ASSINATURAS - LAYOUT PROFISSIONAL
            # ========================================
            
            # Título da seção
            assinaturas_title = ParagraphStyle(
                'AssinaturasTitle',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=20,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph("ASSINATURAS", assinaturas_title))
            story.append(Spacer(1, 0.3*cm))
            
            # ========================================
            # ASSINATURA DO CLIENTE (Pessoa que Coletou)
            # ========================================
            
            # Nome completo
            cliente_nome_style = ParagraphStyle(
                'ClienteNome',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=5
            )
            story.append(Paragraph(f"RETIRADO POR: {coleta_data.get('nome_retirada', 'N/A').upper()}", cliente_nome_style))
            
            # Linha pontilhada para assinatura (mais larga e visível)
            linha_assinatura = Drawing(12*cm, 0.8*cm)
            linha_assinatura.add(Line(0, 0.4*cm, 12*cm, 0.4*cm, 
                                     strokeColor=colors.black,
                                     strokeWidth=1,
                                     strokeDashArray=[3, 3]))
            story.append(linha_assinatura)
            
            # Texto "Assinatura" abaixo da linha
            assinatura_label_style = ParagraphStyle(
                'AssinaturaLabel',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica',
                spaceAfter=8
            )
            story.append(Paragraph("Assinatura do Cliente", assinatura_label_style))
            
            # CPF/Documento
            doc_cliente_style = ParagraphStyle(
                'DocCliente',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=8
            )
            story.append(Paragraph(f"CPF/RG: {coleta_data.get('documento_retirada', '_________________')}", doc_cliente_style))
            
            story.append(Spacer(1, 0.5*cm))
            
            # ========================================
            # ASSINATURA DO FUNCIONÁRIO (Conferente)
            # ========================================
            
            story.append(Paragraph(f"LIBERADO POR: {coleta_data.get('nome_conferente', 'N/A').upper()}", cliente_nome_style))
            
            # Linha pontilhada para assinatura
            linha_funcionario = Drawing(12*cm, 0.8*cm)
            linha_funcionario.add(Line(0, 0.4*cm, 12*cm, 0.4*cm,
                                      strokeColor=colors.black,
                                      strokeWidth=1,
                                      strokeDashArray=[3, 3]))
            story.append(linha_funcionario)
            
            # Texto "Assinatura" abaixo
            story.append(Paragraph("Assinatura do Funcionário Responsável", assinatura_label_style))
            
            # CPF do conferente
            story.append(Paragraph(f"CPF: {coleta_data.get('cpf_conferente', '_________________')}", doc_cliente_style))
            
            story.append(Spacer(1, 0.5*cm))
            
            # ========================================
            # ÁREA PARA ANEXAR DOCUMENTO (MUITO MAIOR)
            # ========================================
            
            # Título com instrução
            doc_title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.black,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=10
            )
            story.append(Paragraph("⚠️ ANEXAR CÓPIA DO DOCUMENTO DE IDENTIFICAÇÃO ABAIXO ⚠️", doc_title_style))
            
            # Retângulo para colar documento (otimizado para caber em 1 página)
            doc_drawing = Drawing(16*cm, 4*cm)
            
            # Retângulo tracejado bem destacado
            rect = Rect(0, 0, 16*cm, 4*cm)
            rect.strokeColor = colors.black
            rect.strokeWidth = 2
            rect.strokeDashArray = [8, 4]
            rect.fillColor = colors.whitesmoke
            doc_drawing.add(rect)
            
            # Texto dentro do retângulo
            from reportlab.graphics.shapes import String
            texto_centralizado = String(8*cm, 2*cm, 
                                       "COLAR CÓPIA DO DOCUMENTO AQUI",
                                       fontSize=16,
                                       fillColor=colors.grey,
                                       textAnchor='middle')
            doc_drawing.add(texto_centralizado)
            
            # Moldura interna (guia visual)
            moldura_interna = Rect(0.3*cm, 0.3*cm, 15.4*cm, 3.4*cm)
            moldura_interna.strokeColor = colors.lightgrey
            moldura_interna.strokeWidth = 1
            moldura_interna.strokeDashArray = [3, 3]
            moldura_interna.fillColor = None
            doc_drawing.add(moldura_interna)
            
            story.append(doc_drawing)
            story.append(Spacer(1, 0.5*cm))
            
            # Rodapé com data/hora de emissão
            rodape_style = ParagraphStyle(
                'Rodape',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
                fontName='Helvetica'
            )
            data_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
            story.append(Paragraph(f"Recibo emitido em {data_emissao} pelo Sistema SAP", rodape_style))
            
            # Construir PDF
            doc.build(story)

            current_app.logger.info(
                "Recibo de coleta gerado com sucesso",
                extra={
                    "pedido_id": coleta_data.get("pedido_id"),
                    "arquivo": filepath,
                    "quantidade_itens": len(coleta_data.get("itens_coleta", [])),
                },
            )
            return filepath
            
        except Exception as e:
            details = {
                "pedido_id": coleta_data.get("pedido_id"),
                "arquivo": filepath,
                "diretorio": receipts_dir,
                "error": str(e),
            }
            current_app.logger.error(
                "Erro ao gerar recibo de coleta",
                exc_info=e,
                extra=details,
            )
            raise FileProcessingError(
                message="Falha ao gerar recibo de coleta em PDF",
                details=details,
            ) from e

    @staticmethod
    def enfileirar_recibo_pdf(coleta_data: Dict) -> Optional[str]:
        """
        Tenta enfileirar a geração do recibo em background.
        
        Returns:
            Optional[str]: ID do job enfileirado ou None caso não seja possível.
        """
        try:
            from meu_app.queue import enqueue_pdf_job
        except ImportError as exc:  # pragma: no cover - cenário inesperado
            current_app.logger.error(
                "Erro ao importar fila para geração de recibo",
                exc_info=exc,
            )
            return None
        
        try:
            return enqueue_pdf_job(coleta_data)
        except Exception as exc:  # pragma: no cover - execução depende do ambiente
            current_app.logger.warning(
                "Falha ao enfileirar geração assíncrona de recibo, utilizando fallback síncrono",
                exc_info=exc,
                extra={"pedido_id": coleta_data.get("pedido_id")},
            )
            return None
