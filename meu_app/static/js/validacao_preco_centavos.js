document.addEventListener('DOMContentLoaded', () => {
    const mensagemErro = 'Use vírgula para separar os centavos (ex.: 10,50).';

    const registrarCampo = (input) => {
        if (!input || input.dataset.centavosWatch === 'true') {
            return;
        }
        input.dataset.centavosWatch = 'true';
        input.addEventListener('blur', () => validarCampo(input));
        input.addEventListener('input', () => {
            if (input.validationMessage) {
                input.setCustomValidity('');
            }
        });
    };

    const validarCampo = (input) => {
        if (!input) return true;
        const valor = (input.value || '').trim();
        if (!valor) {
            input.setCustomValidity('');
            return true;
        }
        if (!valor.includes(',')) {
            input.setCustomValidity(mensagemErro);
            input.reportValidity();
            return false;
        }
        input.setCustomValidity('');
        return true;
    };

    const campos = document.querySelectorAll('input[data-requer-centavos="true"]');
    campos.forEach(registrarCampo);

    document.addEventListener('input', (event) => {
        const alvo = event.target;
        if (alvo && alvo.matches('input[data-requer-centavos="true"]')) {
            registrarCampo(alvo);
        }
    }, true);

    document.addEventListener('submit', (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        const camposForm = form.querySelectorAll('input[data-requer-centavos="true"]');
        for (const campo of camposForm) {
            if (!validarCampo(campo)) {
                event.preventDefault();
                event.stopPropagation();
                campo.focus();
                break;
            }
        }
    }, true);
});
