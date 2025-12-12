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
    const limparFilaBtn = document.getElementById('limparFilaBtn');
    const painelEmptyState = document.querySelector('.comprovante-panel .empty-state');
    const compartilhadosUrl = form.dataset.compartilhadosUrl;
    const descartarCompartilhadoUrl = form.dataset.descartarCompUrl;
    const listaCompartilhados = document.getElementById('listaComprovantesDisponiveis');
    const contadorCompartilhados = document.getElementById('contadorComprovantesDisponiveis');
    const campoCompartilhadoId = document.getElementById('comprovante_compartilhado_id');
    const avisoCompartilhado = document.getElementById('avisoComprovanteCompartilhado');
    const cancelarCompartilhadoBtn = document.getElementById('cancelarCompartilhado');
    const masterSelectCheckbox = document.getElementById('selecionar_todos');
    const shareItemIdInput = document.getElementById('compartilhar_item_id');
    const shareItemValorInput = document.getElementById('compartilhar_item_valor');
    const shareItemFilenameInput = document.getElementById('compartilhar_item_filename');
    const carteiraCreditoInput = document.getElementById('carteira_credito_id');
    const carteiraPanel = document.getElementById('carteiraPanel');
    const carteiraAviso = document.getElementById('carteiraSelecionadaAviso');
    const removerCreditoBtn = document.getElementById('removerCreditoBtn');
    const getSelecionarCheckboxes = () => Array.from(document.querySelectorAll('input[data-action="selecionar"]'));
    const getShareCheckboxes = () => Array.from(document.querySelectorAll('input[data-share-checkbox]'));
    const uncheckShareCheckboxes = () => {
        getShareCheckboxes().forEach((cb) => {
            cb.checked = false;
        });
    };
    const getShareSelectionId = () => (shareItemIdInput ? shareItemIdInput.value : '');
    const clearShareHiddenFields = (alsoUncheck = false) => {
        if (shareItemIdInput) shareItemIdInput.value = '';
        if (shareItemValorInput) shareItemValorInput.value = '';
        if (shareItemFilenameInput) shareItemFilenameInput.value = '';
        if (alsoUncheck) {
            getShareCheckboxes().forEach((cb) => {
                cb.checked = false;
            });
        }
    };
    const setShareHiddenFields = (id, valor, filename) => {
        if (shareItemIdInput) shareItemIdInput.value = id || '';
        if (shareItemValorInput) {
            if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
                shareItemValorInput.value = '';
            } else {
                shareItemValorInput.value = Number(valor).toFixed(2);
            }
        }
        if (shareItemFilenameInput) {
            shareItemFilenameInput.value = filename || '';
        }
    };
    const dropOverlay = document.getElementById('dropOverlay');
    const dropzone = document.querySelector('.dropzone');
    const filaRecibosLista = document.getElementById('filaRecibosLista');
    const modal = document.getElementById('comprovanteModal');
    const modalBody = document.getElementById('comprovanteModalBody');
    const modalTitle = document.getElementById('comprovanteModalTitulo');

    if (ocrStatus) {
        ocrStatus.style.display = 'none';
    }

    const fila = [];
    let processando = false;
    let itemSelecionadoId = null;
    let comprovantesDisponiveis = [];
    let bulkSelecting = false;

    let carteiraSelecionada = null;

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

    const atualizarCarteiraUI = () => {
        if (carteiraAviso) {
            if (carteiraSelecionada) {
                const valorTexto = carteiraSelecionada.valor !== null && carteiraSelecionada.valor !== undefined
                    ? formatBRL(carteiraSelecionada.valor)
                    : 'Crédito selecionado';
                const descricao = carteiraSelecionada.descricao ? ` (${carteiraSelecionada.descricao})` : '';
                carteiraAviso.textContent = `${valorTexto}${descricao} será aplicado automaticamente.`;
                carteiraAviso.style.display = 'block';
            } else {
                carteiraAviso.textContent = '';
                carteiraAviso.style.display = 'none';
            }
        }
        if (removerCreditoBtn) {
            removerCreditoBtn.style.display = carteiraSelecionada ? 'inline-flex' : 'none';
        }
    };

    const aplicarCreditoCarteira = (botao) => {
        if (!botao || !carteiraCreditoInput) return;
        const creditoId = Number(botao.dataset.id);
        if (!creditoId) return;
        const rawValor = botao.dataset.valor;
        const valorNumero = rawValor ? Number(rawValor) : null;
        carteiraSelecionada = {
            id: creditoId,
            valor: Number.isFinite(valorNumero) ? valorNumero : null,
            descricao: botao.dataset.descricao || '',
        };
        carteiraCreditoInput.value = String(creditoId);
        if (valorInput) {
            const atual = parseValor(valorInput.value) || 0;
            if (!atual && carteiraSelecionada.valor !== null) {
                setValorFormatado(carteiraSelecionada.valor);
            }
        }
        atualizarCarteiraUI();
    };

    const removerCreditoSelecionado = () => {
        if (carteiraCreditoInput) {
            carteiraCreditoInput.value = '';
        }
        carteiraSelecionada = null;
        atualizarCarteiraUI();
    };

    atualizarCarteiraUI();

    const togglePainelEmptyState = (hasContent) => {
        if (painelEmptyState) {
            painelEmptyState.style.display = hasContent ? 'none' : 'block';
        }
        if (!ocrStatus) return;
        ocrStatus.style.display = hasContent ? 'flex' : 'none';
        if (!hasContent) {
            ocrStatus.innerHTML = '';
        }
    };

    const getStatusBadgeClass = (status) => ({
        aguardando: 'status-aguardando',
        processando: 'status-processando',
        concluido: 'status-concluido',
        erro: 'status-erro',
    }[status] || '');

    const updateLimparFilaState = () => {
        if (!limparFilaBtn) return;
        limparFilaBtn.disabled = fila.length === 0;
    };

    const atualizarContadorCompartilhados = (quantidade) => {
        if (contadorCompartilhados) {
            contadorCompartilhados.textContent = `${quantidade} ativos`;
        }
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
        updateLimparFilaState();
        if (!fila.length) {
            filaLista.innerHTML = '<div class="fila-vazia">Nenhum comprovante enfileirado.</div>';
            return;
        }

        const shareSelecionadoId = getShareSelectionId();

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
            const badgeClass = getStatusBadgeClass(item.status);

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

        const valorReconhecido = item.result && item.result.valor_encontrado !== undefined && item.result.valor_encontrado !== null
            ? formatBRL(parseValor(item.result.valor_encontrado) || item.result.valor_encontrado)
            : '—';
        const valorNumericoReconhecido = item.result && item.result.valor_encontrado !== undefined && item.result.valor_encontrado !== null
            ? parseValor(item.result.valor_encontrado)
            : null;
        const idReconhecido = item.result && item.result.id_transacao_encontrado ? item.result.id_transacao_encontrado : '—';
        const dataReconhecida = item.result && item.result.data_encontrada ? item.result.data_encontrada : '—';

            const validacao = item.result && item.result.validacao_recebedor ? item.result.validacao_recebedor : null;
            const baseState = validacao ? (validacao.valido === true ? 'ok' : 'fail') : 'unknown';

            const pixValor = (item.result && item.result.chave_pix_recebedor) ? item.result.chave_pix_recebedor : '—';
            const cnpjValor = (item.result && item.result.cnpj_recebedor) ? item.result.cnpj_recebedor : '—';
        const idValor = (item.result && item.result.id_transacao_encontrado) ? item.result.id_transacao_encontrado : '—';
        const idState = (item.result && item.result.id_transacao_encontrado) ? 'ok' : 'unknown';

            const statusIcon = (state) => (state === 'ok' ? '🟢' : state === 'fail' ? '🔴' : '⚪');

            const falhaCard = baseState === 'fail';
            const shareValorAttr = valorNumericoReconhecido !== null ? valorNumericoReconhecido.toFixed(2) : '';
            const shareCheckedAttr = shareSelecionadoId && shareSelecionadoId === item.id ? 'checked' : '';
            const shareDisabledAttr = falhaCard ? 'disabled' : '';
            const encodedFileName = item.file && item.file.name ? encodeURIComponent(item.file.name) : '';

            wrapper.innerHTML = `
                <div class="fila-header">
                    <div>
                        <div class="fila-nome">${item.file.name}</div>
                        <div class="fila-meta"></div>
                    </div>
                    <div class="fila-header-actions">
                        <span class="fila-status ${badgeClass}">${statusLabel}</span>
                        ${!falhaCard ? `
                        <label class="fila-checkbox">
                            <input type="checkbox" data-action="selecionar" data-id="${item.id}" data-valor="${valorNumericoReconhecido !== null ? valorNumericoReconhecido : ''}">
                            Selecionar
                        </label>` : ''}
                        <button type="button" class="btn btn-secondary" data-action="remover" ${item.status === 'processando' ? 'disabled' : ''}>
                            Remover
                        </button>
                    </div>
                </div>
                <div class="fila-resumo">
                    <div><strong>Valor do Comprovante:</strong> ${valorReconhecido}</div>
                    <div><strong>ID.:</strong> ${idReconhecido} ${statusIcon(idState)} ${idState === 'ok' ? '(ID VALIDADO)' : ''}</div>
                    <div><strong>DATA:</strong> ${dataReconhecida}</div>
                </div>
                <div class="highlight-list">
                    <div>PIX RECEBEDOR: ${pixValor} ${statusIcon(baseState)}</div>
                    <div>CNPJ RECEBEDOR: ${cnpjValor} ${statusIcon(baseState)}</div>
                </div>
                <div class="share-inline">
                    <label>
                        <input type="checkbox"
                               name="disponibilizar_comprovante"
                               value="on"
                               data-share-checkbox
                               data-id="${item.id}"
                               data-valor="${shareValorAttr}"
                               data-filename="${encodedFileName}"
                               ${shareCheckedAttr}
                               ${shareDisabledAttr}>
                        Disponibilizar este comprovante para outro pedido após salvar
                    </label>
                </div>
                <div class="fila-footer">
                    <button type="button" class="btn btn-secondary" data-action="ver-comprovante" data-id="${item.id}">
                        Ver comprovante
                    </button>
                </div>
            `;
            if (falhaCard) {
                wrapper.classList.add('error-state');
            }
            filaLista.appendChild(wrapper);
        });
    };

    const enqueueFiles = (fileList) => {
        const files = Array.from(fileList || []);
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
        updateQueueUI();
        processarFila();
    };

    const toggleDropOverlay = (show) => {
        if (dropOverlay) {
            dropOverlay.style.display = show ? 'block' : 'none';
        }
        if (dropzone) {
            dropzone.classList.toggle('active', !!show);
        }
    };

    const renderComprovantesCompartilhados = (lista = []) => {
        if (!listaCompartilhados) return;
        comprovantesDisponiveis = lista;
        listaCompartilhados.innerHTML = '';
        atualizarContadorCompartilhados(lista.length);
        if (!lista.length) {
            listaCompartilhados.innerHTML = '<div class="fila-vazia">Nenhum comprovante compartilhado no momento.</div>';
            return;
        }

        lista.forEach((item) => {
            const card = document.createElement('div');
            const ativo = Number(campoCompartilhadoId?.value || 0) === item.id;
            card.className = `shared-card${ativo ? ' selecionado' : ''}`;
            card.dataset.id = item.id;
            card.innerHTML = `
                <strong>Pedido #${item.pedido_id} · ${item.cliente}</strong>
                <span>Valor sugerido: <strong>${formatBRL(item.valor_sugerido || 0)}</strong></span>
                <span>Data do comprovante: ${item.data_comprovante || '—'}</span>
                ${item.id_transacao ? `<span>ID: ${item.id_transacao}</span>` : ''}
                <span>Disponibilizado por ${item.compartilhado_por || 'Financeiro'} em ${item.compartilhado_em || '-'}</span>
                <div class="fila-actions">
                    <button type="button" class="btn btn-secondary" data-action="usar" data-id="${item.id}">Usar</button>
                    <button type="button" class="btn btn-secondary" data-action="descartar" data-id="${item.id}">Descartar</button>
                    ${item.recibo_url ? `<a class="btn btn-secondary" href="${item.recibo_url}" target="_blank">Ver recibo</a>` : ''}
                </div>
            `;
            listaCompartilhados.appendChild(card);
        });
    };

    const carregarComprovantesCompartilhados = () => {
        if (!compartilhadosUrl) return;
        fetch(compartilhadosUrl)
            .then((resp) => resp.json())
            .then((data) => {
                renderComprovantesCompartilhados(data.comprovantes || []);
            })
            .catch((error) => {
                console.error('Erro ao carregar comprovantes compartilhados', error);
            });
    };

    const aplicarComprovanteCompartilhado = (item) => {
        if (!item) return;
        campoCompartilhadoId.value = item.id;
        if (valorInput && item.valor_sugerido) {
            setValorFormatado(Number(item.valor_sugerido));
        }
        if (idTransacaoInput) {
            idTransacaoInput.value = item.id_transacao || '';
        }
        if (dataComprovanteInput) {
            dataComprovanteInput.value = item.data_comprovante || '';
        }
        if (bancoEmitenteInput) bancoEmitenteInput.value = item.banco_emitente || '';
        if (avisoCompartilhado) {
            avisoCompartilhado.style.display = 'block';
        }
        if (reciboInput) {
            reciboInput.disabled = true;
        }
        uncheckShareCheckboxes();
        renderComprovantesCompartilhados(comprovantesDisponiveis);
    };

    const cancelarUsoCompartilhado = () => {
        campoCompartilhadoId.value = '';
        if (reciboInput) {
            reciboInput.disabled = false;
        }
        if (avisoCompartilhado) {
            avisoCompartilhado.style.display = 'none';
        }
        renderComprovantesCompartilhados(comprovantesDisponiveis);
    };

    const descartarComprovanteCompartilhado = (id) => {
        if (!descartarCompartilhadoUrl) return;
        fetch(descartarCompartilhadoUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : '',
            },
            body: JSON.stringify({ id }),
        })
            .then(() => carregarComprovantesCompartilhados())
            .catch((error) => console.error('Erro ao descartar comprovante compartilhado', error));
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
        togglePainelEmptyState(false);
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
        const ocrMessage = data.ocr_message || 'Dados disponíveis para revisão.';
        const isSuccessState = treatedAsSuccess.includes(ocrStatusText);
        const icon = ocrStatusText === 'failed' ? '⚠️' : (ocrStatusText === 'fallback' ? '🛠️' : '🤖');

        togglePainelEmptyState(true);
        ocrStatus.innerHTML = '';

        const infoBox = document.createElement('div');
        infoBox.className = 'painel-info';
        infoBox.style.borderLeftColor = isSuccessState ? (ocrStatusText === 'fallback' ? '#1f618d' : '#0f8a4b') : '#b54f00';
        infoBox.innerHTML = `
            <div style="font-weight:600;">${icon} ${fileName ? fileName : 'Comprovante processado'}</div>
            <div style="font-size:0.9rem; margin-top:4px;">${ocrMessage}</div>
        `;
        ocrStatus.appendChild(infoBox);

        if (ocrStatusText === 'fallback') {
            const fallbackInfo = document.createElement('div');
            fallbackInfo.className = 'painel-info';
            fallbackInfo.style.borderLeftColor = '#1f618d';
            fallbackInfo.innerHTML = 'Modo offline ativado: confira os valores manualmente.';
            ocrStatus.appendChild(fallbackInfo);
        }

        const dataPoints = [];
        if (data.valor_encontrado !== undefined && data.valor_encontrado !== null) {
            const valorNumerico = parseValor(data.valor_encontrado);
            dataPoints.push({
                label: 'Valor reconhecido',
                value: valorNumerico !== null ? formatBRL(valorNumerico) : data.valor_encontrado,
            });
        }
        if (data.id_transacao_encontrado) {
            dataPoints.push({ label: 'Protocolo / ID', value: data.id_transacao_encontrado });
        }
        if (data.data_encontrada) {
            dataPoints.push({ label: 'Data do comprovante', value: data.data_encontrada });
        }
        if (data.banco_emitente) {
            dataPoints.push({ label: 'Banco remetente', value: data.banco_emitente });
        }

        if (dataPoints.length) {
            const grid = document.createElement('div');
            grid.className = 'comprovante-resumo';
            dataPoints.forEach((point) => {
                const card = document.createElement('div');
                card.className = 'resumo-card';
                card.innerHTML = `<span>${point.label}</span><strong>${point.value}</strong>`;
                grid.appendChild(card);
            });
            ocrStatus.appendChild(grid);
        } else {
            const noDataDiv = document.createElement('div');
            noDataDiv.className = 'painel-info';
            noDataDiv.style.borderLeftColor = '#b54f00';
            noDataDiv.innerHTML = 'Nenhum dado confiável encontrado neste comprovante. Digite manualmente.';
            ocrStatus.appendChild(noDataDiv);
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

        if (ocrStatusText === 'failed' && !dataPoints.length) {
            const manualDiv = document.createElement('div');
            manualDiv.textContent = '💡 Digite os dados manualmente nos campos abaixo';
            manualDiv.style.color = 'gray';
            manualDiv.style.marginTop = '10px';
            manualDiv.style.fontStyle = 'italic';
            ocrStatus.appendChild(manualDiv);
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
            enqueueFiles(event.target.files);
            reciboInput.value = '';
        });
    }

    if (dropzone) {
        ['dragenter', 'dragover'].forEach((evt) => {
            dropzone.addEventListener(evt, (event) => {
                event.preventDefault();
                event.stopPropagation();
                toggleDropOverlay(true);
            });
        });

        ['dragleave', 'dragend', 'drop'].forEach((evt) => {
            dropzone.addEventListener(evt, (event) => {
                event.preventDefault();
                event.stopPropagation();
                toggleDropOverlay(false);
            });
        });

        dropzone.addEventListener('drop', (event) => {
            if (!event.dataTransfer) return;
            enqueueFiles(event.dataTransfer.files);
        });

        dropzone.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                dropzone.click();
            }
        });
    }

    if (filaRecibosLista) {
        filaRecibosLista.setAttribute('role', 'region');
        filaRecibosLista.setAttribute('aria-live', 'polite');
    }

    const abrirModalComprovante = (item) => {
        if (!item || !item.file) return;
        const url = URL.createObjectURL(item.file);
        const tipo = item.file.type || '';

        if (!modal || !modalBody || !modalTitle) {
            window.open(url, '_blank', 'noopener');
            return;
        }

        modalTitle.textContent = `Comprovante: ${item.file.name}`;
        modalBody.innerHTML = '';

        if (tipo.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = url;
            img.alt = item.file.name;
            modalBody.appendChild(img);
        } else {
            const frame = document.createElement('iframe');
            frame.src = url;
            frame.title = item.file.name;
            modalBody.appendChild(frame);
        }
        modal.setAttribute('aria-hidden', 'false');
        modal.dataset.url = url;
    };

    const fecharModalComprovante = () => {
        if (!modal) return;
        const url = modal.dataset.url;
        if (url) {
            URL.revokeObjectURL(url);
            delete modal.dataset.url;
        }
        modal.setAttribute('aria-hidden', 'true');
        if (modalBody) {
            modalBody.innerHTML = '<p class="empty-state">Selecione um comprovante para visualizar.</p>';
        }
    };

    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target.dataset.modalClose !== undefined || event.target.classList.contains('modal-backdrop')) {
                fecharModalComprovante();
            }
        });
        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                fecharModalComprovante();
            }
        });
    }

    updateLimparFilaState();

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
                    limparCampoStatus();
                }
                if (getShareSelectionId() === item.id) {
                    clearShareHiddenFields(true);
                }
                updateQueueUI();
            }
            if (action === 'ver-comprovante') {
                event.preventDefault();
                abrirModalComprovante(item);
            }
        });
    }

    if (filaLista) {
        filaLista.addEventListener('change', (event) => {
            const checkbox = event.target.closest('input[data-action="selecionar"]');
            if (!checkbox || !valorInput) return;
            const rawValor = checkbox.dataset.valor;
            const valorNumero = rawValor ? Number(rawValor) : null;
            if (valorNumero === null || Number.isNaN(valorNumero)) return;

            const atual = parseValor(valorInput.value) || 0;
            const novo = checkbox.checked ? atual + valorNumero : Math.max(0, atual - valorNumero);
            setValorFormatado(novo);

            if (masterSelectCheckbox && !bulkSelecting) {
                const todos = getSelecionarCheckboxes();
                const todosMarcados = todos.length > 0 && todos.every((cb) => cb.checked);
                masterSelectCheckbox.checked = todosMarcados;
            }
        });
    }

    if (carteiraPanel) {
        carteiraPanel.addEventListener('click', (event) => {
            const botao = event.target.closest('button[data-action]');
            if (!botao) return;
            const action = botao.dataset.action;
            if (action === 'usar-credito') {
                event.preventDefault();
                aplicarCreditoCarteira(botao);
            }
            if (action === 'remover-credito') {
                event.preventDefault();
                removerCreditoSelecionado();
            }
        });
    }

    if (filaLista) {
        filaLista.addEventListener('change', (event) => {
            const shareBox = event.target.closest('input[data-share-checkbox]');
            if (!shareBox) return;
            if (shareBox.checked) {
                getShareCheckboxes().forEach((cb) => {
                    if (cb !== shareBox) cb.checked = false;
                });
                let valorShare = shareBox.dataset.valor ? Number(shareBox.dataset.valor) : null;
                if (valorShare === null || Number.isNaN(valorShare)) {
                    const manualValor = window.prompt('Informe o valor deste comprovante (use vírgula para os centavos):', '');
                    if (manualValor === null) {
                        shareBox.checked = false;
                        return;
                    }
                    const parsedManual = parseValor(manualValor);
                    if (parsedManual === null) {
                        window.alert('Valor inválido. Operação cancelada.');
                        shareBox.checked = false;
                        return;
                    }
                    valorShare = parsedManual;
                    shareBox.dataset.valor = parsedManual.toFixed(2);
                }
                let decodedName = '';
                if (shareBox.dataset.filename) {
                    try {
                        decodedName = decodeURIComponent(shareBox.dataset.filename);
                    } catch (_) {
                        decodedName = shareBox.dataset.filename;
                    }
                }
                setShareHiddenFields(shareBox.dataset.id || '', valorShare, decodedName);
                const selectCheckbox = filaLista.querySelector(`input[data-action="selecionar"][data-id="${shareBox.dataset.id}"]`);
                if (selectCheckbox && !selectCheckbox.checked) {
                    selectCheckbox.checked = true;
                    selectCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
                }
            } else if (getShareSelectionId() === shareBox.dataset.id) {
                clearShareHiddenFields(false);
            }
        });
    }

    if (masterSelectCheckbox && filaLista) {
        masterSelectCheckbox.addEventListener('change', () => {
            bulkSelecting = true;
            const marcar = masterSelectCheckbox.checked;
            let atual = parseValor(valorInput.value) || 0;
            let delta = 0;
            const todos = getSelecionarCheckboxes();
            todos.forEach((cb) => {
                const rawValor = cb.dataset.valor;
                const valorNumero = rawValor ? Number(rawValor) : null;
                const estava = cb.checked;
                cb.checked = marcar;
                if (valorNumero !== null && !Number.isNaN(valorNumero)) {
                    if (marcar && !estava) delta += valorNumero;
                    if (!marcar && estava) delta -= valorNumero;
                }
            });
            if (valorInput && delta !== 0) {
                const novo = Math.max(0, atual + delta);
                setValorFormatado(novo);
            }
            bulkSelecting = false;
        });
    }

    if (listaCompartilhados) {
        listaCompartilhados.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-action]');
            if (!btn) return;
            const id = Number(btn.dataset.id);
            if (!id) return;
            if (btn.dataset.action === 'usar') {
                const item = comprovantesDisponiveis.find((comp) => comp.id === id);
                aplicarComprovanteCompartilhado(item);
            }
            if (btn.dataset.action === 'descartar') {
                const confirmar = window.confirm('Deseja remover este comprovante compartilhado da lista?');
                if (confirmar) descartarComprovanteCompartilhado(id);
            }
        });
    }

    if (cancelarCompartilhadoBtn) {
        cancelarCompartilhadoBtn.addEventListener('click', (event) => {
            event.preventDefault();
            cancelarUsoCompartilhado();
        });
    }

    if (limparFilaBtn) {
        limparFilaBtn.addEventListener('click', () => {
            if (!fila.length) return;
            const confirmar = window.confirm('Remover todos os comprovantes da fila?');
            if (!confirmar) return;
            fila.length = 0;
            itemSelecionadoId = null;
            limparCampoStatus();
            clearShareHiddenFields(true);
            updateQueueUI();
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
        if (reciboInput && (!campoCompartilhadoId || !campoCompartilhadoId.value)) {
            const selecionados = getSelecionarCheckboxes().filter((cb) => cb.checked);
            if (selecionados.length) {
                const dt = new DataTransfer();
                selecionados.forEach((cb) => {
                    const item = fila.find((i) => i.id === cb.dataset.id);
                    if (item && item.file) {
                        dt.items.add(item.file);
                    }
                });
                if (dt.files.length) {
                    reciboInput.files = dt.files;
                }
            }
        }

        const totalPedido = parseFloat(form.dataset.total) || 0;
        const totalPago = parseFloat(form.dataset.pago) || 0;
        const novoValor = parseValor(valorInput.value) || 0;
        valorInput.value = novoValor.toFixed(2);

        if (totalPedido && totalPago + novoValor > totalPedido) {
            const confirmar = window.confirm('⚠️ O valor inserido excede o total do pedido.\nDeseja continuar mesmo assim?');
            if (!confirmar) event.preventDefault();
        }
    });

    carregarComprovantesCompartilhados();
});
