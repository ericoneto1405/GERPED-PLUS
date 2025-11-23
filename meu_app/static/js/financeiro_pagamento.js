document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Script financeiro_pagamento.js carregado');
    
    const form = document.getElementById('form-pagamento');
    if (!form) {
        console.error('❌ Formulário #form-pagamento não encontrado');
        return;
    }
    console.log('✅ Formulário encontrado');

    const reciboInput = document.getElementById('recibo');
    const valorInput = document.getElementById('valor');
    const idTransacaoInput = document.querySelector('input[name="id_transacao"]');
    const ocrStatus = document.getElementById('ocr-status-principal');  // NOVO: elemento principal visível
    const metodoPagamentoInput = document.getElementById('metodo_pagamento');
    const ocrUrl = form.dataset.ocrUrl;
    
    // Campos hidden para dados do OCR
    const dataComprovanteInput = document.getElementById('data_comprovante');
    const bancoEmitenteInput = document.getElementById('banco_emitente');
    const agenciaRecebedorInput = document.getElementById('agencia_recebedor');
    const contaRecebedorInput = document.getElementById('conta_recebedor');
    const chavePixRecebedorInput = document.getElementById('chave_pix_recebedor');
    
    console.log('📍 OCR URL:', ocrUrl);
    console.log('📍 Elementos:', {
        reciboInput: !!reciboInput,
        valorInput: !!valorInput,
        idTransacaoInput: !!idTransacaoInput,
        ocrStatus: !!ocrStatus
    });

    const formatBRL = (valor) => {
        try {
            return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch (_) {
            return `R$ ${valor.toFixed(2).replace('.', ',')}`;
        }
    };

    const setValorFormatado = (numero) => {
        if (numero === null || numero === undefined || !valorInput) return;
        valorInput.value = formatBRL(numero);
        valorInput.dataset.rawValue = numero.toFixed(2);
    };

    const parseValor = (valor) => {
        if (typeof valor === 'number') {
            return Number.isFinite(valor) ? valor : null;
        }
        if (typeof valor === 'string') {
            let sanitized = valor
                .trim()
                .replace(/\s+/g, '')
                .replace(/^R\$/i, '')
                .replace(/[Oo]/g, '0')
                .replace(/\.(?=\d{3}(?:\D|$))/g, '')
                .replace(',', '.');

            const parts = sanitized.split('.');
            if (parts.length > 2) {
                const decimal = parts.pop();
                sanitized = parts.join('') + '.' + decimal;
            }

            const match = sanitized.match(/(\d+)(?:\.(\d+))?/);
            if (!match) return null;

            let numeric = Number(match[0]);
            if (Number.isNaN(numeric)) {
                return null;
            }

            return Math.round((numeric + Number.EPSILON) * 100) / 100;
        }
        return null;
    };

    if (metodoPagamentoInput) {
        metodoPagamentoInput.addEventListener('input', function () {
            if (this.value.toLowerCase().includes('pix')) {
                reciboInput.placeholder = 'Comprovante PIX (recomendado para segurança)';
                reciboInput.style.border = '2px solid #ffc107';
                reciboInput.style.backgroundColor = '#fffbf0';
            } else {
                reciboInput.placeholder = 'Recibo de Pagamento (opcional)';
                reciboInput.style.border = '';
                reciboInput.style.backgroundColor = '';
            }
        });
    }

    form.addEventListener('submit', (event) => {
        const totalPedido = parseFloat(form.dataset.total) || 0;
        const totalPago = parseFloat(form.dataset.pago) || 0;
        const novoValor = parseValor(valorInput.value) || 0;

        // Antes de enviar, garantir que o backend receba no formato 1234.56
        valorInput.value = novoValor.toFixed(2);

        if (totalPedido && (totalPago + novoValor) > totalPedido) {
            const confirmar = window.confirm(
                '⚠️ O valor inserido excede o total do pedido.\nDeseja continuar mesmo assim?'
            );
            if (!confirmar) {
                event.preventDefault();
            }
        }
    });

    if (reciboInput) {
        console.log('✅ Listener de upload registrado no campo recibo');
        
        reciboInput.addEventListener('change', (event) => {
            console.log('📁 Arquivo selecionado, iniciando upload OCR...');
            
            const { files } = event.target;
            if (!files || !files[0]) {
                console.warn('⚠️ Nenhum arquivo selecionado');
                return;
            }
            
            console.log('📁 Arquivo:', files[0].name, '- Tamanho:', files[0].size, 'bytes');

            if (!ocrUrl) {
                console.error('❌ Endpoint OCR não configurado (data-ocr-url)');
                return;
            }

            // Mostrar loading animado
            ocrStatus.innerHTML = `
                <div class="ocr-loading">
                    <div class="ocr-spinner"></div>
                    <div>
                        <div style="font-size: 1.1em;">🔍 Conferindo Pagamento...</div>
                        <div style="font-size: 0.85em; font-weight: normal; margin-top: 5px;">
                            Aguarde, estamos validando o comprovante
                        </div>
                    </div>
                </div>
            `;
            ocrStatus.style.display = 'block';

            const formData = new FormData();
            formData.append('recibo', files[0]);
            const csrfTokenInput = form.querySelector('input[name="csrf_token"]');
            if (csrfTokenInput) {
                formData.append('csrf_token', csrfTokenInput.value);
            }

            console.log('🌐 Enviando request para:', ocrUrl);
            
            fetch(ocrUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : ''
                }
            })
                .then((response) => {
                    console.log('📥 Response status:', response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    console.log('✅ OCR retorno completo:', data);
                    let foundSomething = false;
                    ocrStatus.innerHTML = '';

                    if (data.error) {
                        ocrStatus.textContent = `❌ Erro: ${data.error}`;
                        ocrStatus.style.color = 'red';
                        return;
                    }

                    const ocrStatusText = data.ocr_status || 'unknown';
                    const ocrMessage = data.ocr_message || '';
                    const treatedAsSuccess = ['success', 'fallback'];
                    const isSuccessState = treatedAsSuccess.includes(ocrStatusText);

                    const statusDiv = document.createElement('div');
                    statusDiv.style.marginBottom = '10px';
                    statusDiv.style.fontWeight = 'bold';
                    if (isSuccessState) {
                        const icon = ocrStatusText === 'fallback' ? '🛠️' : '🤖';
                        statusDiv.textContent = `${icon} ${ocrMessage}`;
                    } else {
                        statusDiv.textContent = `⚠️ ${ocrMessage}`;
                    }
                    statusDiv.style.color = isSuccessState ? (ocrStatusText === 'fallback' ? '#1f618d' : 'green') : 'orange';
                    ocrStatus.appendChild(statusDiv);

                    if (ocrStatusText === 'fallback') {
                        const fallbackInfo = document.createElement('div');
                        fallbackInfo.style.marginTop = '6px';
                        fallbackInfo.style.fontSize = '0.9em';
                        fallbackInfo.style.color = '#1f618d';
                        fallbackInfo.textContent = 'Modo offline ativado: confira os valores manualmente.';
                        ocrStatus.appendChild(fallbackInfo);
                    }

                    // ML (beta) apenas informativo: não bloqueia decisões
                    if (data.ml_status || data.ml_confidence !== undefined) {
                        const mlBox = document.createElement('div');
                        mlBox.style.marginTop = '8px';
                        mlBox.style.padding = '10px';
                        mlBox.style.borderRadius = '6px';
                        mlBox.style.background = '#f5f7fb';
                        mlBox.style.border = '1px dashed #cfd6e6';
                        const conf = data.ml_confidence !== undefined && data.ml_confidence !== null
                            ? (Number(data.ml_confidence) * 100).toFixed(2) + '%'
                            : '—';
                        mlBox.innerHTML = `
                            <div style="font-weight: 600; color: #34495e;">
                                🤖 ML (beta) – apenas para consulta
                            </div>
                            <div style="font-size: 0.95em; color: #5a6b7b; margin-top: 4px;">
                                Status: <strong>${data.ml_status || 'indefinido'}</strong> | Confiança: <strong>${conf}</strong><br>
                                Este resultado não bloqueia o fluxo até o modelo estar 100% treinado.
                            </div>
                        `;
                        ocrStatus.appendChild(mlBox);
                    }

                    if (data.valor_encontrado !== undefined && data.valor_encontrado !== null) {
                        console.log('💰 Valor encontrado pelo OCR:', data.valor_encontrado);
                        const valorNumerico = parseValor(data.valor_encontrado);
                        console.log('💰 Valor parseado:', valorNumerico);
                        
                        if (valorNumerico !== null) {
                            setValorFormatado(valorNumerico);
                            console.log('✅ Campo valor preenchido com:', valorInput.value);
                            foundSomething = true;
                        } else {
                            console.warn('⚠️ Não foi possível parsear o valor:', data.valor_encontrado);
                        }
                        const valorStatus = document.createElement('div');
                        if (valorNumerico !== null) {
                            valorStatus.textContent = '✅ Valor preenchido automaticamente!';
                            valorStatus.style.color = 'green';
                        } else {
                            valorStatus.textContent =
                                '⚠️ OCR encontrou possível valor, mas não foi possível converter. Verifique manualmente.';
                            valorStatus.style.color = 'orange';
                        }
                        valorStatus.style.marginTop = '5px';
                        ocrStatus.appendChild(valorStatus);
                    }

                    if (data.id_transacao_encontrado) {
                        idTransacaoInput.value = data.id_transacao_encontrado;
                        const idStatus = document.createElement('div');
                        idStatus.innerHTML = `✅ ID da Transação: <strong>${data.id_transacao_encontrado}</strong>`;
                        idStatus.style.color = 'green';
                        idStatus.style.marginTop = '5px';
                        ocrStatus.appendChild(idStatus);
                        foundSomething = true;
                    }

                    // Preencher campos hidden com dados do OCR
                    if (data.data_encontrada && dataComprovanteInput) {
                        dataComprovanteInput.value = data.data_encontrada;
                        const dataStatus = document.createElement('div');
                        dataStatus.innerHTML = `📅 Data: <strong>${data.data_encontrada}</strong>`;
                        dataStatus.style.color = 'blue';
                        dataStatus.style.marginTop = '5px';
                        ocrStatus.appendChild(dataStatus);
                    }

                    if (data.banco_emitente && bancoEmitenteInput) {
                        bancoEmitenteInput.value = data.banco_emitente;
                        const bancoStatus = document.createElement('div');
                        bancoStatus.innerHTML = `🏦 Banco: <strong>${data.banco_emitente}</strong>`;
                        bancoStatus.style.color = 'blue';
                        bancoStatus.style.marginTop = '5px';
                        ocrStatus.appendChild(bancoStatus);
                    }
                    
                    if (data.agencia_recebedor && agenciaRecebedorInput) {
                        agenciaRecebedorInput.value = data.agencia_recebedor;
                    }
                    
                    if (data.conta_recebedor && contaRecebedorInput) {
                        contaRecebedorInput.value = data.conta_recebedor;
                    }
                    
                    if (data.chave_pix_recebedor && chavePixRecebedorInput) {
                        chavePixRecebedorInput.value = data.chave_pix_recebedor;
                    }
                    
                    // Manter o arquivo selecionado para que seja enviado junto com o formulário
                    console.log('📌 Mantendo arquivo selecionado para enviar com o pagamento');
                    
                    // NOVO: Validação do recebedor (MAIS VISÍVEL E PROFISSIONAL)
                    if (data.validacao_recebedor) {
                        const validacao = data.validacao_recebedor;
                        const validacaoDiv = document.createElement('div');
                        validacaoDiv.className = 'validation-box';
                        
                        if (validacao.valido === true) {
                            validacaoDiv.classList.add('validation-success');
                            validacaoDiv.innerHTML = `
                                <div style="font-size: 1.2em; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 1.5em;">✅</span>
                                    <span>Pagamento para conta CORRETA</span>
                                </div>
                                <div style="font-size: 1em; font-weight: normal; padding: 10px; background: rgba(40, 167, 69, 0.1); border-radius: 6px;">
                                    ${validacao.motivo.join('<br>')}
                                </div>
                                <div style="margin-top: 10px; font-size: 0.95em; text-align: right;">
                                    Confiança: <strong>${validacao.confianca}%</strong>
                                </div>
                            `;
                        } else if (validacao.valido === false) {
                            validacaoDiv.classList.add('validation-warning');
                            validacaoDiv.innerHTML = `
                                <div style="font-size: 1.2em; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 1.5em;">⚠️</span>
                                    <span>ATENÇÃO: Recebedor Não Confere!</span>
                                </div>
                                <div style="font-size: 0.95em; font-weight: normal; padding: 10px; background: rgba(255, 193, 7, 0.1); border-radius: 6px; margin-bottom: 10px;">
                                    ${validacao.motivo.join('<br>')}
                                </div>
                                <div style="padding: 12px; background: #fff; border: 2px dashed #d9534f; border-radius: 6px; text-align: center;">
                                    <div style="font-size: 1.1em; color: #d9534f; font-weight: bold; margin-bottom: 5px;">
                                        ⚠️ VERIFIQUE O COMPROVANTE
                                    </div>
                                    <div style="font-size: 0.9em; font-weight: normal; color: #666;">
                                        Confirme que o pagamento foi feito para a conta da empresa
                                    </div>
                                </div>
                            `;
                        } else {
                            validacaoDiv.classList.add('validation-info');
                            validacaoDiv.innerHTML = `
                                <div style="font-size: 1.1em; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 1.5em;">ℹ️</span>
                                    <span>Validação Manual Necessária</span>
                                </div>
                                <div style="font-size: 0.95em; font-weight: normal;">
                                    Dados do recebedor não encontrados no comprovante.
                                </div>
                                <div style="margin-top: 12px; padding: 12px; background: rgba(33, 150, 243, 0.1); border-radius: 6px; font-weight: normal;">
                                    <div style="margin-bottom: 5px; font-weight: bold;">Verifique se o pagamento foi para:</div>
                                    <div style="font-size: 0.9em; line-height: 1.6;">
                                        📧 PIX: <strong>pix@gruposertao.com</strong><br>
                                        🏢 CNPJ: <strong>30.080.209/0004-16</strong>
                                    </div>
                                </div>
                            `;
                        }
                        
                        ocrStatus.appendChild(validacaoDiv);
                    }

                    if (ocrStatusText === 'failed') {
                        const manualDiv = document.createElement('div');
                        manualDiv.textContent =
                            '💡 Digite os dados manualmente nos campos abaixo';
                        manualDiv.style.color = 'gray';
                        manualDiv.style.marginTop = '10px';
                        manualDiv.style.fontStyle = 'italic';
                        ocrStatus.appendChild(manualDiv);
                    } else if (!foundSomething && treatedAsSuccess.includes(ocrStatusText)) {
                        const noDataDiv = document.createElement('div');
                        noDataDiv.textContent =
                            '⚠️ Nenhum dado encontrado no recibo. Digite manualmente.';
                        noDataDiv.style.color = 'orange';
                        noDataDiv.style.marginTop = '5px';
                        ocrStatus.appendChild(noDataDiv);
                    }
                })
                .catch((error) => {
                    console.error('❌ ERRO no fetch do OCR:', error);
                    console.error('❌ Stack trace:', error.stack);
                    ocrStatus.innerHTML = `
                        <div style="color: orange; font-weight: bold; margin-bottom: 10px;">
                            ⚠️ OCR temporariamente indisponível
                        </div>
                        <div style="color: gray; font-style: italic; margin-top: 5px;">
                            💡 Digite os dados manualmente nos campos abaixo
                        </div>
                    `;
                });
        });
    }
    if (valorInput) {
        valorInput.addEventListener('blur', () => {
            const parsed = parseValor(valorInput.value);
            if (parsed !== null) {
                setValorFormatado(parsed);
            }
        });
    }
});
