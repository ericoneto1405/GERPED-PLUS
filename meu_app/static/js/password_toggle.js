(function () {
    const init = () => {
        const buttons = document.querySelectorAll('.toggle-password');
        buttons.forEach((button) => {
            button.addEventListener('click', () => {
                const targetId = button.getAttribute('data-target');
                const field = button.closest('.password-field');
                const input = targetId
                    ? document.getElementById(targetId)
                    : field
                        ? field.querySelector('input[type="password"], input[type="text"]')
                        : null;
                if (!input) return;
                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                button.classList.toggle('is-visible', isHidden);
                button.setAttribute('aria-pressed', String(isHidden));
                button.setAttribute('aria-label', isHidden ? 'Ocultar senha' : 'Mostrar senha');
            });
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
