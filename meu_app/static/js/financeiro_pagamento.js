document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-pagamento');
    if (!form) return;

    const reciboInput = document.getElementById('recibo');
    const valorInput = document.getElementById('valor');
    const idTransacaoInput = document.querySelector('input[name="id_transacao"]');
    const dataComprovanteInput = document.getElementById('data_comprovante');
    const bancoEmitenteInput = document.getElementById('banco_emitente');
    const agenciaRecebedorInput = document.getElementById('agencia_recebedor');
    const contaRecebedorInput = document.getElementById('conta_recebedor');
    const chavePixRecebedorInput = document.getElementById('chave_pix_recebedor');
    const metodoPagamentoInput = document.getElementById('metodo_pagamento');
    const csrfTokenInput = form.querySelector('input[name="csrf_token"]');
    const ocrStatus = document.getElementById('ocr-status-principal');
    const filaLista = document.getElementById('filaRecibosLista');
    const ocrUrl = form.dataset.ocrUrl;

    const fila = [];
    let processando = false;
    let itemSelecionadoId = null;

    const formatBRL = (valor) => {
        try {
            return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch (_) {
            return `R$ ${Number(valor).toFixed(2).replace('.', ',')}`;
        }
    };

    const formatBytes = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    };

    const setValorFormatado = (numero) => {
        if (numero === null || numero === undefined || !valorInput) return;
        valorInput.value = formatBRL(numero);
        valorInput.dataset.rawValue = numero.toFixed(2);
    };

    const parseValor = (valor) => {
        if (typeof valor === 'number') return Number.isFinite(valor) ? valor : null;
        if (typeof valor !== 'string') return null;

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
        const numeric = Number(match[0]);
        if (Number.isNaN(numeric)) return null;
        return Math.round((numeric + Number.EPSILON) * 100) / 100;
    };

    const anexarArquivoParaEnvio = (file) => {
        if (!reciboInput || !file) return;
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        reciboInput.files = dataTransfer.files;
    };

    const updateQueueUI = () => {
        if (!filaLista) return;
        filaLista.innerHTML = '';
        if (!fila.length) {
            filaLista.innerHTML = '<div class="fila-vazia">Nenhum comprovante enfileirado.</div>';
            return;
        }

        fila.forEach((item) => {
            const wrapper = document.createElement('div');
            wrapper.className = `fila-item ${item.status}${item.id === itemSelecionadoId ? ' selecionado' : ''}`;
            wrapper.dataset.id = item.id;
            const statusLabel = {
                aguardando: 'Aguardando na fila',
                processando: 'Processando...',
                concluido: 'Processado',
                erro: 'Falhou',
            }[item.status] || 'Indefinido';

            const highlights = [];
            if (item.result) {
                if (item.result.valor_encontrado !== undefined && item.result.valor_encontrado !== null) {
                    highlights.push(`💰 ${formatBRL(parseValor(item.result.valor_encontrado) || item.result.valor_encontrado)}`);
                }
                if (item.result.id_transacao_encontrado) {
                    highlights.push(`🔗 ${item.result.id_transacao_encontrado}`);
                }
                if (item.result.data_encontrada) {
                    highlights.push(`📅 ${item.result.data_encontrada}`);
                }
            }

            wrapper.innerHTML = `
                <div class="fila-header">
                    <div>
                        <div class="fila-nome">${item.file.name}</div>
                        <div class="fila-meta">${formatBytes(item.file.size)}</div>
                    </div>
                    <span class="fila-status">${statusLabel}</span>
                </div>
                <div class="fila-meta">${item.statusMessage || ''}</div>
                ${
                    highlights.length
                        ? `<div class="fila-resumo">${highlights.map((h) => `<span>${h}</span>`).join('')}</div>`
                        : ''
                }
                <div class="fila-actions">
                    <button type="button" class="btn btn-secondary" data-action="usar" ${item.status !== 'concluido' ? 'disabled' : ''}>
                        Usar este comprovante
                    </button>
                    <button type="button" class="btn btn-secondary" data-action="remover" ${item.status === 'processando' ? 'disabled' : ''}>
                        Remover
                    </button>
                </div>
            `;
            filaLista.appendChild(wrapper);
        });
    };

    const processarFila = () => {
        if (processando) return;
        const proximo = fila.find((item) => item.status === 'aguardando');
        if (!proximo) return;

        proximo.status = 'processando';
        proximo.statusMessage = 'Enviando para OCR...';
        processando = true;
        updateQueueUI();

        const formData = new FormData();
        formData.append('recibo', proximo.file);
        if (csrfTokenInput) formData.append('csrf_token', csrfTokenInput.value);

        fetch(ocrUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : '',
            },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                proximo.status = 'concluido';
                proximo.result = data;
                proximo.statusMessage = data.ocr_message || 'Processado';
                processando = false;
                updateQueueUI();
                if (!itemSelecionadoId) {
                    aplicarResultadoNoFormulario(proximo);
                }
                processarFila();
            })
            .catch((error) => {
                proximo.status = 'erro';
                proximo.statusMessage = `Erro: ${error.message}`;
                processando = false;
                updateQueueUI();
                processarFila();
            });
    };

    const limparCampoStatus = () => {
        if (!ocrStatus) return;
        ocrStatus.innerHTML = '';
        ocrStatus.style.display = 'block';
    };

    const aplicarResultadoNoFormulario = (item) => {
        if (!item || !item.result) return;
        const data = item.result;
        limparCampoStatus();
        itemSelecionadoId = item.id;
        preencherCamposComDados(data);
        anexarArquivoParaEnvio(item.file);
        renderPainelPrincipal(data, item.file.name);
        updateQueueUI();
    };

    const preencherCamposComDados = (data) => {
        let encontrouInformacao = false;
        if (data.valor_encontrado !== undefined && data.valor_encontrado !== null) {
            const valorNumerico = parseValor(data.valor_encontrado);
            if (valorNumerico !== null) {
                setValorFormatado(valorNumerico);
                encontrouInformacao = true;
            }
        }
        if (data.id_transacao_encontrado && idTransacaoInput) {
            idTransacaoInput.value = data.id_transacao_encontrado;
            encontrouInformacao = true;
        }
        if (data.data_encontrada && dataComprovanteInput) {
            dataComprovanteInput.value = data.data_encontrada;
        }
        if (data.banco_emitente && bancoEmitenteInput) {
            bancoEmitenteInput.value = data.banco_emitente;
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
        return encontrouInformacao;
    };

    const renderPainelPrincipal = (data, fileName) => {
        if (!ocrStatus) return;
        const treatedAsSuccess = ['success', 'fallback'];
        const ocrStatusText = data.ocr_status || 'unknown';
        const ocrMessage = data.ocr_message || '';
        const isSuccessState = treatedAsSuccess.includes(ocrStatusText);
        let foundSomething = false;
        if (data.valor_encontrado !== undefined && data.valor_encontrado !== null) foundSomething = true;
        if (data.id_transacao_encontrado) foundSomething = true;

        ocrStatus.innerHTML = `
            <div class="ocr-loading" style="background: ${isSuccessState ? '#e4fff2' : '#fff5e1'}; color: ${isSuccessState ? '#145a32' : '#7d5100'};">
                <div>
                    <div style="font-size: 1.05em; font-weight: 600;">
                        ${fileName ? `📄 ${fileName}` : 'Resultados do OCR'}
                    </div>
                    <div style="font-size: 0.9em; font-weight: normal; margin-top: 5px;">
                        ${ocrMessage}
                    </div>
                </div>
            </div>
        `;

        const statusDiv = document.createElement('div');
        statusDiv.style.marginTop = '10px';
        statusDiv.style.fontWeight = 'bold';
        statusDiv.style.color = isSuccessState ? (ocrStatusText === 'fallback' ? '#1f618d' : 'green') : 'orange';
        const icon = isSuccessState ? (ocrStatusText === 'fallback' ? '🛠️' : '🤖') : '⚠️';
        statusDiv.textContent = `${icon} ${ocrMessage}`;
        ocrStatus.appendChild(statusDiv);

        if (ocrStatusText === 'fallback') {
            const fallbackInfo = document.createElement('div');
            fallbackInfo.style.marginTop = '6px';
            fallbackInfo.style.fontSize = '0.9em';
            fallbackInfo.style.color = '#1f618d';
            fallbackInfo.textContent = 'Modo offline ativado: confira os valores manualmente.';
            ocrStatus.appendChild(fallbackInfo);
        }

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
            const valorNumerico = parseValor(data.valor_encontrado);
            const valorStatus = document.createElement('div');
            valorStatus.style.marginTop = '5px';
            if (valorNumerico !== null) {
                valorStatus.textContent = '✅ Valor preenchido automaticamente!';
                valorStatus.style.color = 'green';
            } else {
                valorStatus.textContent =
                    '⚠️ OCR encontrou possível valor, mas não foi possível converter. Verifique manualmente.';
                valorStatus.style.color = 'orange';
            }
            ocrStatus.appendChild(valorStatus);
        }

        if (data.id_transacao_encontrado) {
            const idStatus = document.createElement('div');
            idStatus.innerHTML = `✅ ID da Transação: <strong>${data.id_transacao_encontrado}</strong>`;
            idStatus.style.color = 'green';
            idStatus.style.marginTop = '5px';
            ocrStatus.appendChild(idStatus);
        }

        if (data.data_encontrada) {
            const dataStatus = document.createElement('div');
            dataStatus.innerHTML = `📅 Data: <strong>${data.data_encontrada}</strong>`;
            dataStatus.style.color = 'blue';
            dataStatus.style.marginTop = '5px';
            ocrStatus.appendChild(dataStatus);
        }

        if (data.banco_emitente) {
            const bancoStatus = document.createElement('div');
            bancoStatus.innerHTML = `🏦 Banco: <strong>${data.banco_emitente}</strong>`;
            bancoStatus.style.color = 'blue';
            bancoStatus.style.marginTop = '5px';
            ocrStatus.appendChild(bancoStatus);
        }

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

        if (data.ocr_status === 'failed') {
            const manualDiv = document.createElement('div');
            manualDiv.textContent = '💡 Digite os dados manualmente nos campos abaixo';
            manualDiv.style.color = 'gray';
            manualDiv.style.marginTop = '10px';
            manualDiv.style.fontStyle = 'italic';
            ocrStatus.appendChild(manualDiv);
        } else if (!foundSomething && treatedAsSuccess.includes(ocrStatusText)) {
            const noDataDiv = document.createElement('div');
            noDataDiv.textContent = '⚠️ Nenhum dado encontrado no recibo. Digite manualmente.';
            noDataDiv.style.color = 'orange';
            noDataDiv.style.marginTop = '5px';
            ocrStatus.appendChild(noDataDiv);
        }
    };

    if (metodoPagamentoInput && reciboInput) {
        metodoPagamentoInput.addEventListener('input', function () {
            if (this.value.toLowerCase().includes('pix')) {
                reciboInput.style.border = '2px solid #ffc107';
                reciboInput.style.backgroundColor = '#fffbf0';
            } else {
                reciboInput.style.border = '';
                reciboInput.style.backgroundColor = '';
            }
        });
    }

    if (reciboInput) {
        reciboInput.addEventListener('change', (event) => {
            const files = Array.from(event.target.files || []);
            if (!files.length || !ocrUrl) return;
            files.forEach((file) => {
                fila.push({
                    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
                    file,
                    status: 'aguardando',
                    statusMessage: 'Aguardando na fila',
                    result: null,
                });
            });
            reciboInput.value = '';
            updateQueueUI();
            processarFila();
        });
    }

    if (filaLista) {
        filaLista.addEventListener('click', (event) => {
            const actionBtn = event.target.closest('button[data-action]');
            if (!actionBtn) return;
            const itemDiv = actionBtn.closest('.fila-item');
            if (!itemDiv) return;
            const item = fila.find((i) => i.id === itemDiv.dataset.id);
            if (!item) return;

            const action = actionBtn.dataset.action;
            if (action === 'usar' && item.status === 'concluido') {
                aplicarResultadoNoFormulario(item);
            }
            if (action === 'remover' && item.status !== 'processando') {
                const index = fila.indexOf(item);
                if (index >= 0) fila.splice(index, 1);
                if (itemSelecionadoId === item.id) {
                    itemSelecionadoId = null;
                    if (ocrStatus) ocrStatus.innerHTML = '';
                }
                updateQueueUI();
            }
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

    form.addEventListener('submit', (event) => {
        const totalPedido = parseFloat(form.dataset.total) || 0;
        const totalPago = parseFloat(form.dataset.pago) || 0;
        const novoValor = parseValor(valorInput.value) || 0;
        valorInput.value = novoValor.toFixed(2);

        if (totalPedido && totalPago + novoValor > totalPedido) {
            const confirmar = window.confirm('⚠️ O valor inserido excede o total do pedido.\nDeseja continuar mesmo assim?');
            if (!confirmar) event.preventDefault();
        }
    });
});
