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
    const adminCheckUrl = form.dataset.adminCheckUrl;
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
    const anexosValoresInput = document.getElementById('anexos_valores');
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

    if (ocrStatus) {
        ocrStatus.style.display = 'none';
    }

    const fila = [];
    let processando = false;
    let itemSelecionadoId = null;
    let comprovantesDisponiveis = [];
    let bulkSelecting = false;
    const selecionadosValores = new Map();
    let atualizandoValorPorSelecao = false;
    let valorControladoPorSelecao = false;
    let carteiraSelecionada = null;

    const anexosPersistidos = [];
    const anexosExistentesData = form.dataset.anexosExistentes;
    if (anexosExistentesData) {
        try {
            const parsed = JSON.parse(anexosExistentesData);
            if (Array.isArray(parsed)) {
                parsed.forEach((info) => {
                    if (!info || !info.url || !info.id) return;
                    const valorNumero = typeof info.valor === 'number' ? info.valor : Number(info.valor);
                    anexosPersistidos.push({
                        id: String(info.id),
                        nome: info.nome || 'Comprovante',
                        valor: Number.isFinite(valorNumero) ? valorNumero : null,
                        data: info.data_pagamento || info.data || '',
                        metodo: info.metodo_pagamento || info.metodo || '',
                        servidor: true,
                        serverUrl: info.url,
                        pagamentoId: info.pagamento_id || null,
                    });
                });
            }
        } catch (err) {
            console.warn('Falha ao carregar anexos existentes do pedido', err);
        }
    }

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

    const abrirComprovanteEmNovaAba = (url, temporario) => {
        if (!url) return;
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.target = '_blank';
        anchor.rel = 'noopener';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        if (temporario) {
            setTimeout(() => {
                try {
                    URL.revokeObjectURL(url);
                } catch (error) {
                    console.warn('Não foi possível liberar a visualização temporária:', error);
                }
            }, 120000);
        }
    };

    const abrirComprovante = (item) => {
        if (!item) return;
        let url = null;
        let temporario = false;
        if (item.file instanceof File) {
            try {
                url = URL.createObjectURL(item.file);
                temporario = true;
            } catch (error) {
                console.error('Erro ao preparar comprovante temporário:', error);
            }
        } else if (item.serverUrl) {
            url = item.serverUrl;
        }
        if (!url) {
            window.alert('Não foi possível abrir este comprovante.');
            return;
        }
        abrirComprovanteEmNovaAba(url, temporario);
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

    const solicitarSenhaAdminFinanceiro = async () => {
        if (!adminCheckUrl) {
            window.alert('Endpoint de validação de senha não configurado.');
            return false;
        }
        const senha = window.prompt('Informe a senha do administrador para liberar esta ação:');
        if (senha === null) return false;
        if (!senha.trim()) {
            window.alert('Senha é obrigatória.');
            return false;
        }
        const payload = { senha: senha.trim() };
        try {
            const resp = await fetch(adminCheckUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfTokenInput ? csrfTokenInput.value : '',
                },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                window.alert(data.message || 'Senha inválida ou não autorizada.');
                return false;
            }
            return true;
        } catch (error) {
            console.error('Falha ao validar senha admin no financeiro', error);
            window.alert('Não foi possível validar a senha. Verifique sua conexão.');
            return false;
        }
    };

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

    const atualizarMasterCheckboxEstado = () => {
        if (!masterSelectCheckbox) return;
        const checkboxes = getSelecionarCheckboxes();
        if (!checkboxes.length) {
            masterSelectCheckbox.checked = false;
            masterSelectCheckbox.indeterminate = false;
            return;
        }
        const marcados = checkboxes.filter((cb) => cb.checked).length;
        masterSelectCheckbox.checked = marcados === checkboxes.length;
        masterSelectCheckbox.indeterminate = marcados > 0 && marcados < checkboxes.length;
    };

    const atualizarValorTotalSelecionados = () => {
        if (!valorInput) return;
        if (!selecionadosValores.size) {
            if (valorControladoPorSelecao) {
                atualizandoValorPorSelecao = true;
                setValorFormatado(0);
                atualizandoValorPorSelecao = false;
                valorControladoPorSelecao = false;
            }
            return;
        }
        let total = 0;
        selecionadosValores.forEach((valor) => {
            if (Number.isFinite(valor)) {
                total += valor;
            }
        });
        atualizandoValorPorSelecao = true;
        setValorFormatado(total);
        atualizandoValorPorSelecao = false;
        valorControladoPorSelecao = true;
    };

    const limparSelecionados = () => {
        selecionadosValores.clear();
        getSelecionarCheckboxes().forEach((cb) => {
            cb.checked = false;
        });
        valorControladoPorSelecao = false;
        atualizarValorTotalSelecionados();
        atualizarMasterCheckboxEstado();
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
        updateLimparFilaState();
        const fragment = document.createDocumentFragment();
        const shareSelecionadoId = getShareSelectionId();
        const temPersistidos = anexosPersistidos.length > 0;
        const temFila = fila.length > 0;

        const idsAtuais = new Set(fila.map((item) => item.id));
        Array.from(selecionadosValores.keys()).forEach((id) => {
            if (!idsAtuais.has(id)) {
                selecionadosValores.delete(id);
            }
        });

        if (temPersistidos) {
            const heading = document.createElement('div');
            heading.className = 'fila-heading';
            heading.textContent = 'Comprovantes já anexados neste pedido';
            fragment.appendChild(heading);
            anexosPersistidos.forEach((persistido) => {
                const wrapperPersistido = document.createElement('div');
                wrapperPersistido.className = 'fila-item persistido';
                wrapperPersistido.dataset.persistidoId = persistido.id;
                const valorTexto = persistido.valor !== null && persistido.valor !== undefined
                    ? formatBRL(persistido.valor)
                    : '—';
                const metaPartes = [];
                if (persistido.pagamentoId) metaPartes.push(`Pagamento #${persistido.pagamentoId}`);
                if (persistido.metodo) metaPartes.push(persistido.metodo);
                const linkPersistido = persistido.serverUrl
                    ? `<a class="btn btn-secondary" href="${persistido.serverUrl}" target="_blank" rel="noopener">
                            Ver comprovante
                       </a>`
                    : '<span class="text-muted">Arquivo indisponível</span>';
                wrapperPersistido.innerHTML = `
                    <div class="fila-header">
                        <div>
                            <div class="fila-nome">${persistido.nome}</div>
                            <div class="fila-meta">${metaPartes.join(' · ')}</div>
                        </div>
                        <div class="fila-header-actions">
                            <span class="fila-status status-salvo">Salvo</span>
                        </div>
                    </div>
                    <div class="fila-resumo">
                        <div><strong>Valor:</strong> ${valorTexto}</div>
                        <div><strong>Data:</strong> ${persistido.data || '—'}</div>
                    </div>
                    <div class="fila-footer">
                        ${linkPersistido}
                    </div>
                `;
                fragment.appendChild(wrapperPersistido);
            });
            if (temFila) {
                const divider = document.createElement('div');
                divider.className = 'fila-divider';
                fragment.appendChild(divider);
            }
        }

        if (!temFila) {
            const vazio = document.createElement('div');
            vazio.className = temPersistidos ? 'fila-vazia fila-vazia-secundaria' : 'fila-vazia';
            vazio.textContent = temPersistidos ? 'Nenhum comprovante novo enfileirado.' : 'Nenhum comprovante enfileirado.';
            fragment.appendChild(vazio);
            filaLista.innerHTML = '';
            filaLista.appendChild(fragment);
            if (selecionadosValores.size) {
                selecionadosValores.clear();
            }
            atualizarValorTotalSelecionados();
            atualizarMasterCheckboxEstado();
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
            const adminShareUnlocked = !!item.adminShareUnlocked;
            const podeSelecionar = !falhaCard || adminShareUnlocked;
            if (!podeSelecionar && selecionadosValores.has(item.id)) {
                selecionadosValores.delete(item.id);
            }
            if (selecionadosValores.has(item.id)) {
                if (valorNumericoReconhecido !== null && !Number.isNaN(valorNumericoReconhecido)) {
                    selecionadosValores.set(item.id, valorNumericoReconhecido);
                } else {
                    selecionadosValores.delete(item.id);
                }
            }
            const shareValorAttr = valorNumericoReconhecido !== null ? valorNumericoReconhecido.toFixed(2) : '';
            const shareCheckedAttr = shareSelecionadoId && shareSelecionadoId === item.id ? 'checked' : '';
            const shareDisabledAttr = falhaCard && !adminShareUnlocked ? 'disabled' : '';
            const shareHelper = falhaCard && !adminShareUnlocked
                ? `<div class="share-admin-warning">
                        <small>Comprovante reprovado. Apenas administradores podem disponibilizá-lo.</small>
                        <button type="button" class="ghost-btn" data-action="admin-share" data-id="${item.id}">Liberar com senha</button>
                   </div>`
                : '';
            const encodedFileName = item.file && item.file.name ? encodeURIComponent(item.file.name) : '';

            wrapper.innerHTML = `
                    <div class="fila-header">
                        <div>
                            <div class="fila-nome">${item.file.name}</div>
                            <div class="fila-meta"></div>
                        </div>
                        <div class="fila-header-actions">
                            <span class="fila-status ${badgeClass}">${statusLabel}</span>
                        ${podeSelecionar ? `
                        <label class="fila-checkbox">
                            <input type="checkbox" data-action="selecionar" data-id="${item.id}" data-valor="${valorNumericoReconhecido !== null ? valorNumericoReconhecido : ''}" ${selecionadosValores.has(item.id) ? 'checked' : ''}>
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
                    ${shareHelper}
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
            fragment.appendChild(wrapper);
        });

        filaLista.innerHTML = '';
        filaLista.appendChild(fragment);
        atualizarMasterCheckboxEstado();
        atualizarValorTotalSelecionados();
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
                adminShareUnlocked: false,
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

    updateQueueUI();

    if (filaLista) {
        filaLista.addEventListener('click', (event) => {
            const actionBtn = event.target.closest('button[data-action]');
            if (!actionBtn) return;
            const itemDiv = actionBtn.closest('.fila-item');
            if (!itemDiv) return;
            const persistidoId = itemDiv.dataset.persistidoId;
            const item = persistidoId
                ? anexosPersistidos.find((p) => p.id === persistidoId)
                : fila.find((i) => i.id === itemDiv.dataset.id);
            if (!item) return;

            const action = actionBtn.dataset.action;
            if (action === 'admin-share') {
                event.preventDefault();
                solicitarSenhaAdminFinanceiro().then((autorizado) => {
                    if (!autorizado) return;
                    item.adminShareUnlocked = true;
                    updateQueueUI();
                    window.alert('Compartilhamento liberado para este comprovante.');
                });
                return;
            }
            if (action === 'ver-comprovante') {
                event.preventDefault();
                abrirComprovante(item);
                return;
            }

            if (persistidoId) return;

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
                if (selecionadosValores.has(item.id)) {
                    selecionadosValores.delete(item.id);
                    atualizarValorTotalSelecionados();
                }
                if (getShareSelectionId() === item.id) {
                    clearShareHiddenFields(true);
                }
                updateQueueUI();
            }
        });
    }

    if (filaLista) {
        filaLista.addEventListener('change', (event) => {
            const checkbox = event.target.closest('input[data-action="selecionar"]');
            if (!checkbox || !valorInput) return;
            let rawValor = checkbox.dataset.valor;
            let valorNumero = rawValor ? Number(rawValor) : null;
            if (valorNumero === null || Number.isNaN(valorNumero)) {
                if (checkbox.checked) {
                    const manualValor = window.prompt('Informe o valor deste comprovante (use vírgula para centavos):', '');
                    if (manualValor === null) {
                        checkbox.checked = false;
                        atualizarMasterCheckboxEstado();
                        return;
                    }
                    const parsedManual = parseValor(manualValor);
                    if (parsedManual === null || parsedManual <= 0) {
                        window.alert('Valor inválido. Operação cancelada.');
                        checkbox.checked = false;
                        atualizarMasterCheckboxEstado();
                        return;
                    }
                    valorNumero = parsedManual;
                    checkbox.dataset.valor = parsedManual.toFixed(2);
                } else {
                    selecionadosValores.delete(checkbox.dataset.id);
                    atualizarValorTotalSelecionados();
                    atualizarMasterCheckboxEstado();
                    return;
                }
            }
            const checkboxId = checkbox.dataset.id;
            if (!checkboxId) return;

            if (checkbox.checked) {
                selecionadosValores.set(checkboxId, valorNumero);
            } else {
                selecionadosValores.delete(checkboxId);
            }
            atualizarValorTotalSelecionados();

            if (masterSelectCheckbox && !bulkSelecting) {
                atualizarMasterCheckboxEstado();
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
            const todos = getSelecionarCheckboxes();
            if (!marcar) {
                todos.forEach((cb) => {
                    cb.checked = false;
                });
                selecionadosValores.clear();
            } else {
                selecionadosValores.clear();
                todos.forEach((cb) => {
                    cb.checked = true;
                    const rawValor = cb.dataset.valor;
                    const valorNumero = rawValor ? Number(rawValor) : null;
                    const checkboxId = cb.dataset.id;
                    if (checkboxId && valorNumero !== null && !Number.isNaN(valorNumero)) {
                        selecionadosValores.set(checkboxId, valorNumero);
                    }
                });
            }
            bulkSelecting = false;
            atualizarValorTotalSelecionados();
            atualizarMasterCheckboxEstado();
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

    if (valorInput) {
        valorInput.addEventListener('input', () => {
            if (atualizandoValorPorSelecao) return;
            if (selecionadosValores.size) {
                limparSelecionados();
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
        let anexosMeta = [];
        if (reciboInput && (!campoCompartilhadoId || !campoCompartilhadoId.value)) {
            const selecionados = getSelecionarCheckboxes().filter((cb) => cb.checked);
            if (selecionados.length) {
                const dt = new DataTransfer();
                anexosMeta = selecionados.map((cb) => {
                    const item = fila.find((i) => i.id === cb.dataset.id);
                    if (item && item.file) {
                        dt.items.add(item.file);
                        const valorSelecionado = selecionadosValores.get(cb.dataset.id);
                        return {
                            nome: item.file.name,
                            valor: Number.isFinite(valorSelecionado) ? valorSelecionado : null,
                        };
                    }
                    return null;
                }).filter(Boolean);
                if (dt.files.length) {
                    reciboInput.files = dt.files;
                }
            }
        }
        if (anexosValoresInput) {
            anexosValoresInput.value = anexosMeta.length ? JSON.stringify(anexosMeta) : '';
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
