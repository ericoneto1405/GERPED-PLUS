"""
Serviço de OCR usando Google Vision API - Versão baseada em GCS.
"""
import os
import json
import re
import uuid
from typing import Optional, Dict, List, Tuple
from datetime import datetime
# Importações opcionais (evitar falha em ambientes sem dependências GCP)
try:
    from google.cloud import vision, storage
    from google.api_core.exceptions import NotFound
    _gcp_import_error = None
except Exception as exc:  # pragma: no cover - depende do ambiente
    vision = None  # type: ignore
    storage = None  # type: ignore
    NotFound = Exception  # type: ignore
    _gcp_import_error = exc
from .config import FinanceiroConfig
from .exceptions import OcrProcessingError


class VisionOcrService:
    """Serviço de OCR usando Google Vision API com extração avançada de dados"""
    
    _client = None
    _storage_client = None
    _initialized = False
    MAX_VALID_AMOUNT = 1_000_000_000  # Valores acima disso são tratados como falsos positivos
    
    @classmethod
    def _get_client(cls):
        """
        Obtém o cliente do Google Vision com lazy loading
        Returns:
            vision.ImageAnnotatorClient: Cliente do Google Vision
        """
        if cls._client is None:
            if _gcp_import_error is not None or vision is None:
                raise OcrProcessingError(
                    f"Bibliotecas Google Cloud Vision indisponíveis: {_gcp_import_error}"
                )
            try:
                api_key = FinanceiroConfig.get_google_api_key()
                credentials_path = FinanceiroConfig.get_google_credentials_path()

                client_kwargs = {}

                # For environments blocked on SRV DNS lookups (common in on-prem firewalls),
                # force gRPC to use the native resolver to avoid `_grpclb` queries.
                os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

                client_kwargs.setdefault("client_options", {})

                if api_key:
                    # API Key habilitada: ideal para imagens; PDFs continuarão exigindo credenciais.
                    client_kwargs["client_options"]["api_key"] = api_key
                elif credentials_path and os.path.exists(credentials_path):
                    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                else:
                    raise OcrProcessingError(
                        "Credenciais do Google Vision não configuradas. "
                        "Defina GOOGLE_VISION_API_KEY ou GOOGLE_VISION_CREDENTIALS_PATH."
                    )

                # Força transporte REST para evitar problemas de DNS com gRPC em ambientes restritos.
                client_kwargs["transport"] = client_kwargs.get("transport", "rest")

                print("Inicializando cliente Google Vision...")
                cls._client = vision.ImageAnnotatorClient(**client_kwargs)
                cls._initialized = True
                print("Cliente Google Vision pronto.")
                
            except Exception as e:
                print(f"Erro ao inicializar Google Vision: {e}")
                raise OcrProcessingError(f"Falha ao inicializar Google Vision: {str(e)}")
        
        return cls._client
    
    @classmethod
    def _get_storage_client(cls):
        """Obtém cliente do Google Cloud Storage"""
        if cls._storage_client is None:
            if _gcp_import_error is not None or storage is None:
                raise OcrProcessingError(
                    f"Bibliotecas Google Cloud Storage indisponíveis: {_gcp_import_error}"
                )
            try:
                credentials_path = FinanceiroConfig.get_google_credentials_path()
                if not credentials_path or not os.path.exists(credentials_path):
                    raise OcrProcessingError(
                        "Processamento de PDF requer credenciais de serviço válidas "
                        "(GOOGLE_VISION_CREDENTIALS_PATH)."
                    )

                if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

                cls._storage_client = storage.Client()
            except Exception as e:
                print(f"Erro ao inicializar Storage: {e}")
                raise OcrProcessingError(f"Falha ao inicializar Storage: {str(e)}")
        return cls._storage_client
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Verifica se o Google Vision foi inicializado"""
        return cls._initialized
    
    @staticmethod
    def _split_gcs_uri(uri: str) -> Tuple[str, str]:
        if not uri.startswith("gs://"):
            raise OcrProcessingError(f"URI inválida para GCS: {uri}")
        path = uri[5:]
        bucket, _, blob = path.partition('/')
        if not bucket or not blob:
            raise OcrProcessingError(f"URI incompleta para GCS: {uri}")
        return bucket, blob
    
    @classmethod
    def _upload_pdf_to_gcs(cls, file_path: str) -> str:
        """Carrega PDF para bucket de entrada e retorna URI gs://"""
        if not os.path.exists(file_path):
            raise OcrProcessingError("PDF não encontrado")
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise OcrProcessingError("PDF está vazio")
        
        max_size = FinanceiroConfig.get_max_pdf_size()
        if max_size and file_size > max_size:
            raise OcrProcessingError(f"PDF muito grande ({file_size} bytes). Limite: {max_size} bytes")
        
        storage_client = cls._get_storage_client()
        bucket_name = FinanceiroConfig.get_gcs_input_bucket()
        object_prefix = FinanceiroConfig.get_gcs_input_prefix()
        blob_name = f"{object_prefix}/{uuid.uuid4()}.pdf" if object_prefix else f"{uuid.uuid4()}.pdf"
        
        try:
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path, content_type="application/pdf")
            print(f"PDF enviado para GCS: gs://{bucket_name}/{blob_name}")
            return f"gs://{bucket_name}/{blob_name}"
        except Exception as exc:
            raise OcrProcessingError(f"Falha ao enviar PDF para GCS: {exc}")
    
    @classmethod
    def _prepare_output_uri(cls) -> Tuple[str, str]:
        """Gera URI de saída única para resultados do OCR"""
        bucket = FinanceiroConfig.get_gcs_output_bucket()
        prefix = FinanceiroConfig.get_gcs_output_prefix()
        output_id = uuid.uuid4()
        object_prefix = f"{prefix}/{output_id}" if prefix else str(output_id)
        output_uri = f"gs://{bucket}/{object_prefix}/"
        return output_uri, object_prefix
    
    @classmethod
    def _fetch_output_text(cls, output_uri: str) -> str:
        """Baixa os resultados do Vision do bucket de saída"""
        storage_client = cls._get_storage_client()
        bucket_name, prefix = cls._split_gcs_uri(output_uri)
        # Remover barra final para listagem
        prefix = prefix.rstrip('/')
        
        texts: List[str] = []
        try:
            blobs = list(storage_client.list_blobs(bucket_name, prefix=prefix))
        except Exception as exc:
            raise OcrProcessingError(f"Falha ao listar resultados no GCS: {exc}")
        
        if not blobs:
            raise OcrProcessingError("Vision não retornou resultados para o PDF enviado")
        
        for blob in blobs:
            try:
                data = json.loads(blob.download_as_text())
                for response in data.get('responses', []):
                    full_text = response.get('fullTextAnnotation', {}).get('text')
                    if full_text:
                        texts.append(full_text)
            except Exception as exc:
                print(f"Erro ao ler resultado OCR ({blob.name}): {exc}")
                continue
        
        combined = "\n".join(texts).strip()
        if not combined:
            raise OcrProcessingError("Vision processou o PDF mas não encontrou texto")
        return combined
    
    @classmethod
    def _cleanup_gcs_resources(cls, input_uri: str, output_uri: str):
        """Remove arquivos temporários do GCS"""
        storage_client = cls._get_storage_client()
        
        # Remover PDF de entrada
        try:
            bucket_name, blob_name = cls._split_gcs_uri(input_uri)
            storage_client.bucket(bucket_name).blob(blob_name).delete()
        except NotFound:
            pass
        except Exception as exc:
            print(f"Falha ao remover PDF de entrada no GCS: {exc}")
        
        # Remover resultados
        try:
            bucket_name, prefix = cls._split_gcs_uri(output_uri)
            prefix = prefix.rstrip('/')
            bucket = storage_client.bucket(bucket_name)
            for blob in storage_client.list_blobs(bucket_name, prefix=prefix):
                try:
                    bucket.blob(blob.name).delete()
                except Exception as exc:
                    print(f"Falha ao remover resultado OCR ({blob.name}): {exc}")
        except NotFound:
            pass
        except Exception as exc:
            print(f"Falha ao limpar resultados OCR no GCS: {exc}")
    
    @classmethod
    def _extract_text_from_file(cls, file_path: str) -> str:
        """
        Usa o Google Vision para extrair texto de PDFs (via GCS) ou imagens locais.
        """
        try:
            client = cls._get_client()
            file_ext = os.path.splitext(file_path)[1].lower()
            is_pdf = file_ext == '.pdf'
            
            if is_pdf:
                input_uri = cls._upload_pdf_to_gcs(file_path)
                output_uri, _ = cls._prepare_output_uri()
                
                feature = vision.Feature(type=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
                gcs_source = vision.GcsSource(uri=input_uri)
                input_config = vision.InputConfig(gcs_source=gcs_source, mime_type="application/pdf")
                gcs_destination = vision.GcsDestination(uri=output_uri)
                output_config = vision.OutputConfig(gcs_destination=gcs_destination, batch_size=1)
                
                request = vision.AsyncAnnotateFileRequest(
                    features=[feature],
                    input_config=input_config,
                    output_config=output_config,
                )
                
                print("🔍 Iniciando OCR assíncrono para PDF...")
                operation = client.async_batch_annotate_files(requests=[request])
                timeout = FinanceiroConfig.get_ocr_operation_timeout()
                operation.result(timeout=timeout)
                print("✅ OCR concluído pelo Vision, baixando resultado...")
                
                try:
                    text = cls._fetch_output_text(output_uri)
                finally:
                    cls._cleanup_gcs_resources(input_uri, output_uri)
                
                return text
            
            with open(file_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            detection_type = FinanceiroConfig.get_detection_type()
            if detection_type == 'DOCUMENT_TEXT_DETECTION':
                response = client.document_text_detection(image=image)
            else:
                response = client.text_detection(image=image)
            
            error_info = getattr(response, 'error', None)
            if error_info and getattr(error_info, 'code', 0):
                error_msg = None
                if getattr(error_info, 'message', None):
                    error_msg = error_info.message
                elif getattr(error_info, 'code', None):
                    error_msg = f"Code: {error_info.code}"
                elif str(error_info).strip():
                    error_msg = str(error_info)
                else:
                    error_msg = "Erro desconhecido do Google Vision"
                raise OcrProcessingError(f"Erro do Google Vision: {error_msg}")
            
            texts = []
            for text in response.text_annotations:
                texts.append(text.description)
            
            return '\n'.join(texts) if texts else ""
            
        except OcrProcessingError:
            raise
        except Exception as e:
            print(f"Erro durante extração de texto com Google Vision: {e}")
            raise OcrProcessingError(f"Falha na extração de texto: {str(e)}")

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """
        Extrai o texto completo de um arquivo usando Google Vision.
        
        Args:
            file_path (str): Caminho absoluto do arquivo (PDF ou imagem).
        
        Returns:
            str: Texto reconhecido pelo Vision.
        """
        return cls._extract_text_from_file(file_path)
    
    @staticmethod
    def _find_amount_in_text(text: str) -> Optional[float]:
        """
        Encontra o valor monetário mais provável em uma string de texto,
        dando prioridade a palavras-chave específicas e valores maiores.
        
        Estratégia:
        1. Busca valores após palavras-chave prioritárias (Valor:, Total:, etc)
        2. Se não encontrar, busca TODOS valores e retorna o MAIOR (principal)
        3. Ignora valores muito pequenos (< R$ 5,00) se houver valores maiores
        """
        import unicodedata
        
        # Normalizar acentos
        def remove_accents(s):
            return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
        
        text_normalized = remove_accents(text).upper().replace('\u00A0', ' ').replace('\t', ' ')
        
        # Padrão 1: MÁXIMA PRIORIDADE - Palavras-chave específicas de transação
        # IMPORTANTE: \d+ para aceitar qualquer quantidade de dígitos (não limitar a 3)
        max_priority_patterns = [
            r'(?:VALOR\s+DA\s+TRANSACAO|DADOS\s+DA\s+TRANSACAO[\s\S]{0,100}VALOR)\s*[:\-]?\s*R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})',
            r'(?:VALOR\s+TRANSFERIDO|VALOR\s+DO\s+PAGAMENTO|VALOR\s+DO\s+PIX)\s*[:\-]?\s*R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})',
            r'(?:VALOR\s+LIQUIDO|TOTAL\s+LIQUIDO)\s*[:\-]?\s*R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})',
        ]
        
        lines = [line.strip() for line in text_normalized.splitlines() if line.strip()]

        def extract_numbers(fragment: str) -> list[float]:
            numeros = []
            fragment_clean = fragment.replace('O', '0').replace('º', '0').replace('L', '1')
            has_hint = any(token in fragment_clean for token in ('R$', 'VALOR', 'TOTAL', 'PAGAMENTO', 'PIX'))

            decimal_pattern = r'R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})'
            for match in re.finditer(decimal_pattern, fragment_clean):
                valor_bruto = match.group(1)
                fim = match.end()
                prox = fragment_clean[fim:fim + 1]
                if prox in {'/', '-'} or prox.isdigit():
                    continue
                try:
                    valor = VisionOcrService._parse_currency_value(valor_bruto)
                    if 0 < valor <= VisionOcrService.MAX_VALID_AMOUNT:
                        numeros.append(valor)
                except (ValueError, TypeError):
                    continue

            if has_hint:
                inteiro_pattern = r'R?\$?\s*(\d{1,3}(?:[.\s]\d{3})+)(?![,\d])'
                for match in re.findall(inteiro_pattern, fragment_clean):
                    try:
                        valor = float(match.replace('.', '').replace(' ', ''))
                        if 0 < valor <= VisionOcrService.MAX_VALID_AMOUNT:
                            numeros.append(valor)
                    except (ValueError, TypeError):
                        continue

                plain_pattern = r'R?\$?\s*(\d{4,})'
                for match in re.findall(plain_pattern, fragment_clean):
                    if '/' in match or '-' in match:
                        continue
                    try:
                        valor = float(match)
                        if 0 < valor <= VisionOcrService.MAX_VALID_AMOUNT:
                            numeros.append(valor)
                    except (ValueError, TypeError):
                        continue

            return numeros

        keywords = [
            'VALOR TOTAL',
            'TOTAL DA NOTA',
            'VALOR DA NOTA',
            'TOTAL NF',
            'TOTAL R$',
            'TOTAL GERAL'
        ]

        valores_prioritarios = []
        for idx, line in enumerate(lines):
            snippet = line
            if idx + 1 < len(lines):
                snippet = f"{snippet} {lines[idx + 1]}"
            if any(keyword in snippet for keyword in keywords):
                valores_prioritarios.extend(extract_numbers(snippet))

        if valores_prioritarios:
            valores_prioritarios = [
                v for v in valores_prioritarios
                if 5.0 <= v <= VisionOcrService.MAX_VALID_AMOUNT
            ]
            if valores_prioritarios:
                return max(valores_prioritarios)

        for pattern in max_priority_patterns:
            matches = re.findall(pattern, text_normalized, re.IGNORECASE)
            if matches:
                value_str = matches[0]
                try:
                    return VisionOcrService._parse_currency_value(value_str)
                except (ValueError, TypeError):
                    continue

        high_priority_patterns = [
            r'(?:VALOR|TOTAL)\s*[:\-]?\s*R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})',
            r'(?:TRANSFERIDO|PAGO)\s*[:\-]?\s*R?\$?\s*(\d+(?:[.,\s]\d{3})*[.,]\d{2})',
        ]

        high_priority_values = []
        for pattern in high_priority_patterns:
            matches = re.findall(pattern, text_normalized, re.IGNORECASE)
            for match in matches:
                try:
                    valor = VisionOcrService._parse_currency_value(match)
                    if 0 < valor <= VisionOcrService.MAX_VALID_AMOUNT:
                        high_priority_values.append(valor)
                except (ValueError, TypeError):
                    continue

        if high_priority_values:
            return max(high_priority_values)

        all_values = []
        for line in lines:
            all_values.extend(extract_numbers(line))

        all_values = [
            v for v in all_values
            if 5.0 <= v <= VisionOcrService.MAX_VALID_AMOUNT
        ]
        if not all_values:
            return None

        max_valor = max(all_values)
        if max_valor > VisionOcrService.MAX_VALID_AMOUNT:
            return None

        return max_valor

    @staticmethod
    def _parse_currency_value(value_str: str) -> float:
        """Converte string de valor monetário para float"""
        value_str = value_str.replace(' ', '')
        value_str = value_str.replace('O', '0').replace('o', '0')
        value_str = re.sub(r'(?<=\d)[,\.](?=\d{3}(?:\D|$))', '', value_str)

        if re.fullmatch(r'\d{5,}', value_str):
            return float(value_str)
        if '.' in value_str and ',' in value_str:
            if value_str.rfind('.') > value_str.rfind(','):
                # Formato americano: 1,234.56
                cleaned_value = value_str.replace(',', '')
            else:
                # Formato brasileiro: 1.234,56
                cleaned_value = value_str.replace('.', '').replace(',', '.')
        else:
            # Apenas vírgula ou ponto
            cleaned_value = value_str.replace(',', '.')
        
        return float(cleaned_value)

    @staticmethod
    def _find_transaction_id_in_text(text: str) -> Optional[str]:
        """
        Encontra um ID de transação em uma string de texto.
        Suporta múltiplos padrões de bancos brasileiros.
        """
        import unicodedata
        
        # Normalizar texto removendo acentos para facilitar regex
        def remove_accents(input_str):
            nfkd = unicodedata.normalize('NFKD', input_str)
            return ''.join([c for c in nfkd if not unicodedata.combining(c)])
        
        text_normalized = remove_accents(text).upper()
        
        # Padrão 1: Labels explícitos (prioridade alta)
        # IMPORTANTE: Aceitar IDs numéricos OU alfanuméricos (mínimo 8 chars)
        explicit_patterns = [
            # Mercado Pago e similares - "Número da transação" (numérico OU alfanumérico)
            r'(?:NUMERO\s+DA\s+TRANSACAO|NUMERO\s+TRANSACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            
            # PIX - Diversos formatos
            r'(?:ID\s+DA\s+TRANSACAO|ID\s+TRANSACAO|IDENTIFICACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'\bID\b\s*[:\-]?\s*([A-Z0-9]{8,50})',
            r'(?:CODIGO\s+DA\s+TRANSACAO|CODIGO\s+TRANSACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            
            # Termos comuns
            r'(?:ID\s+PAGAMENTO|PAGAMENTO\s+ID|ID\s+PIX)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:CODIGO\s+DA\s+OPERACAO|COD\.\s+OPERACAO|OPERACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:NUMERO\s+DA\s+OPERACAO|N\.\s+OPERACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:N\.\s+DOCUMENTO|NUMERO\s+DOCUMENTO|DOCUMENTO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:NOSSO\s+NUMERO|NOSSO\s+NUM)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:PROTOCOLO|AUTENTICACAO)\s*[:\-]?\s*([a-zA-Z0-9]{8,50})',
            r'(?:COMPROVACAO|COMPROVANTE)\s*[:\-]?\s*([a-zA-Z0-9]{15,50})',
            
            # Nubank/Inter (UUID-like)
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        ]
        explicit_candidates: List[str] = []
        
        for pattern in explicit_patterns:
            matches = re.findall(pattern, text_normalized, re.IGNORECASE)
            for match in matches:
                candidate = match.strip()
                if re.match(r'^\d{1,2}[/\-\.]\d{1,2}', candidate):
                    continue
                if len(candidate) >= 8:
                    explicit_candidates.append(candidate)
        
        def is_pix_txid(value: str) -> bool:
            return bool(re.fullmatch(r'[ED][0-9]{25,40}', value))
        
        for candidate in explicit_candidates:
            if is_pix_txid(candidate):
                return candidate
        
        # Padrão 2: IDs PIX padrão brasileiro (começam com E ou D)
        # Formato: E00000000202510021939023026977590 (32+ caracteres)
        pix_pattern = r'\b([ED][0-9]{25,40})\b'
        matches = re.findall(pix_pattern, text_normalized)
        if matches:
            # Retornar o mais longo (geralmente mais completo)
            return max(matches, key=len)
        
        # Padrão 3: Sequências alfanuméricas longas (15-50 chars)
        # Após palavras-chave relacionadas a transação
        context_pattern = r'(?:TRANSACAO|PAGAMENTO|PIX|TRANSFERENCIA)\s*[:\-]?\s*([A-Z0-9]{15,50})'
        matches = re.findall(context_pattern, text_normalized)
        if matches:
            return matches[0].strip()
        
        # Padrão 4: Busca genérica por códigos longos
        # Evitar datas (com /) e valores (com , ou R$)
        generic_pattern = r'\b([A-Z0-9]{20,50})\b'
        matches = re.findall(generic_pattern, text_normalized)
        if matches:
            # Filtrar candidatos válidos
            for candidate in matches:
                # Não pode ser só números (pode ser CPF, telefone, etc)
                if not candidate.isdigit():
                    # Não pode ter padrão de data
                    if not re.search(r'\d{2}[/\-\.]\d{2}', candidate):
                        return candidate
        
        for candidate in explicit_candidates:
            if not candidate.isdigit():
                return candidate
        
        for candidate in explicit_candidates:
            if len(candidate) >= 15:
                return candidate
        
        if explicit_candidates:
            return explicit_candidates[0]

        return None

    @staticmethod
    def _find_date_in_text(text: str) -> Optional[str]:
        """
        Encontra data no texto do comprovante.
        """
        text = text.upper()
        
        # Padrões de data brasileira
        date_patterns = [
            r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(?:DATA\s+DA\s+TRANSACAO|DATA\s+DO\s+PAGAMENTO|DATA)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})'  # "15 de janeiro de 2024"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

    @staticmethod
    def _find_bank_info_in_text(text: str) -> Dict[str, Optional[str]]:
        """
        Encontra informações bancárias no texto.
        Inclui dados do RECEBEDOR (para validação) e dados do PAGADOR.
        """
        text_upper = text.upper()
        
        result = {
            'banco_emitente': None,
            'agencia_recebedor': None,
            'conta_recebedor': None,
            'chave_pix_recebedor': None,
            'nome_recebedor': None,      # NOVO: Nome de quem recebeu
            'cnpj_recebedor': None,       # NOVO: CNPJ de quem recebeu
            'cpf_cnpj_recebedor': None    # NOVO: CPF ou CNPJ formatado
        }
        
        # Padrões para banco emitente
        bank_patterns = [
            r'(?:BANCO\s+DO\s+BRASIL|BB|CAIXA\s+ECONOMICA|ITAU|BRADESCO|SANTANDER|NUBANK|INTER|SICOOB|SICREDI)',
            r'(?:BANCO\s+)[A-Z\s]+(?=\s|$)'
        ]
        
        for pattern in bank_patterns:
            matches = re.findall(pattern, text)
            if matches:
                result['banco_emitente'] = matches[0].strip()
                break
        
        # Padrões para agência
        agency_patterns = [
            r'(?:AGENCIA|AG\.?)\s*[:\-]?\s*(\d{4,5})',
            r'(\d{4,5})\s*(?:AGENCIA|AG\.?)'
        ]
        
        for pattern in agency_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result['agencia_recebedor'] = matches[0]
                break
        
        # Padrões para conta
        account_patterns = [
            r'(?:CONTA|CC)\s*[:\-]?\s*(\d{5,15})',
            r'(\d{5,15})\s*(?:CONTA|CC)'
        ]
        
        for pattern in account_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result['conta_recebedor'] = matches[0]
                break
        
        # Padrões para chave PIX (busca abrangente)
        # Busca TODAS as chaves PIX e filtra a da empresa
        pix_empresa = 'pix@gruposertao.com'
        
        pix_patterns = [
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Qualquer email
            r'(\+55\s?\d{2}\s?\d{4,5}[\/\-]?\d{4})',  # Telefone
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # Chave aleatória
        ]
        
        chaves_encontradas = []
        for pattern in pix_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            chaves_encontradas.extend(matches)
        
        # Verificar se alguma chave encontrada é da empresa
        for chave in chaves_encontradas:
            chave_lower = chave.lower().strip()
            pix_empresa_lower = pix_empresa.lower()
            
            if chave_lower == pix_empresa_lower:
                result['chave_pix_recebedor'] = chave
                break
        
        # Se não encontrou a chave da empresa, pegar a primeira chave encontrada (pode ser útil)
        if not result['chave_pix_recebedor'] and chaves_encontradas:
            result['chave_pix_recebedor'] = chaves_encontradas[0]
        
        # NOVO: Extrair CNPJ do recebedor (busca abrangente)
        # Busca TODOS os CNPJs no texto e filtra o da empresa
        cnpj_empresa = '30080209000416'  # Grupo Sertão
        
        # Padrões para encontrar QUALQUER CNPJ no texto
        cnpj_patterns = [
            r'(\d{2}\.?\d{3}\.?\d{3}[\/\-]?\d{3,4}[\/\-]?\d{2})',  # Com formatação
            r'(\d{14})',  # 14 dígitos seguidos
        ]
        
        cnpjs_encontrados = []
        for pattern in cnpj_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                cnpj_limpo = re.sub(r'[^\d]', '', match)
                if len(cnpj_limpo) == 14:
                    cnpjs_encontrados.append({
                        'original': match,
                        'limpo': cnpj_limpo
                    })
        
        # Verificar se algum CNPJ encontrado é da empresa
        for cnpj_data in cnpjs_encontrados:
            if cnpj_data['limpo'] == cnpj_empresa:
                result['cnpj_recebedor'] = cnpj_data['limpo']
                result['cpf_cnpj_recebedor'] = cnpj_data['original']
                break
        
        # NOVO: Extrair nome do recebedor
        # Procurar após palavras-chave "Para:", "Recebedor:", "Favorecido:", "Beneficiário:"
        nome_patterns = [
            r'(?:PARA|RECEBEDOR|FAVORECIDO|BENEFICIARIO)\s*[:\-]?\s*([A-Z][A-Z\s&]{3,50})',
            r'(?:DESTINATARIO|DESTINO)\s*[:\-]?\s*([A-Z][A-Z\s&]{3,50})',
        ]
        
        for pattern in nome_patterns:
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            if matches:
                nome = matches[0].strip()
                # Limpar espaços extras
                nome = ' '.join(nome.split())
                if len(nome) >= 3:  # Nome mínimo razoável
                    result['nome_recebedor'] = nome
                    break
        
        return result
    
    @staticmethod
    def _validar_recebedor(bank_info: Dict, recebedor_esperado: Dict) -> Dict:
        """
        Valida se o recebedor do pagamento é o esperado (Grupo Sertão).
        
        Returns:
            Dict com 'valido', 'motivo', 'confianca'
        """
        validacao = {
            'valido': False,
            'motivo': [],
            'confianca': 0  # 0-100%
        }
        
        pontos = 0
        checks = 0
        
        # Check 1: Chave PIX (50 pontos - mais confiável)
        if bank_info.get('chave_pix_recebedor'):
            checks += 1
            chave_lower = bank_info['chave_pix_recebedor'].lower()
            pix_esperado_lower = recebedor_esperado['pix'].lower()
            
            if chave_lower == pix_esperado_lower:
                pontos += 50
                validacao['motivo'].append(f"✅ Chave PIX correta: {bank_info['chave_pix_recebedor']}")
            else:
                validacao['motivo'].append(f"⚠️ Chave PIX diferente: {bank_info['chave_pix_recebedor']} (esperado: {recebedor_esperado['pix']})")
        
        # Check 2: CNPJ do recebedor (50 pontos - mais confiável)
        if bank_info.get('cnpj_recebedor'):
            checks += 1
            cnpj_limpo = re.sub(r'[^\d]', '', bank_info['cnpj_recebedor'])
            cnpj_esperado = recebedor_esperado['cnpj']
            
            if cnpj_limpo == cnpj_esperado:
                pontos += 50
                validacao['motivo'].append(f"✅ CNPJ correto: {bank_info.get('cpf_cnpj_recebedor', cnpj_limpo)}")
            else:
                validacao['motivo'].append(f"⚠️ CNPJ diferente: {bank_info.get('cpf_cnpj_recebedor')} (esperado: {recebedor_esperado['cnpj_formatado']})")
        
        # Calcular confiança (PIX + CNPJ = 100 pontos possíveis)
        if checks > 0:
            validacao['confianca'] = int((pontos / (checks * 50)) * 100)  # Normalizar para 100%
        
        # Considerar válido se confiança >= 50%
        validacao['valido'] = validacao['confianca'] >= 50
        
        # Se não extraiu nenhum dado do recebedor
        if checks == 0:
            validacao['motivo'].append("ℹ️ Dados do recebedor não encontrados no comprovante (OCR não identificou)")
            validacao['valido'] = None  # Indeterminado
        
        return validacao
    
    @classmethod
    def process_receipt(cls, file_path: str) -> Dict:
        """
        Processa um arquivo de recibo usando Google Vision.
        Retorna um dicionário com todos os dados encontrados.
        """
        try:
            text = cls._extract_text_from_file(file_path)
            if not text:
                return {
                    'amount': None, 
                    'transaction_id': None,
                    'date': None,
                    'bank_info': {},
                    'error': 'Não foi possível extrair texto do documento.'
                }

            # Extrair todos os dados
            amount = cls._find_amount_in_text(text)
            transaction_id = cls._find_transaction_id_in_text(text)
            date = cls._find_date_in_text(text)
            bank_info = cls._find_bank_info_in_text(text)
            
            # NOVO: Validar recebedor (se configurado)
            from .config import FinanceiroConfig
            validacao_recebedor = None
            
            if FinanceiroConfig.validar_recebedor_habilitado():
                recebedor_esperado = FinanceiroConfig.get_recebedor_esperado()
                validacao_recebedor = cls._validar_recebedor(bank_info, recebedor_esperado)

            return {
                'amount': amount,
                'transaction_id': transaction_id,
                'date': date,
                'bank_info': bank_info,
                'validacao_recebedor': validacao_recebedor,  # NOVO campo
                'backend': 'google_vision',
                'raw_text': text,
            }
            
        except OcrProcessingError as e:
            return {
                'amount': None, 
                'transaction_id': None,
                'date': None,
                'bank_info': {},
                'error': str(e),
                'backend': 'google_vision'
            }
        except Exception as e:
            return {
                'amount': None, 
                'transaction_id': None,
                'date': None,
                'bank_info': {},
                'error': f'Erro inesperado no Google Vision: {str(e)}',
                'backend': 'google_vision'
            }
