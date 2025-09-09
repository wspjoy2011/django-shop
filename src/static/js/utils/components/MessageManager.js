export class MessageManager {
    static DEFAULT_CONFIG = {
        alertClasses: {
            success: 'bg-success text-white',
            error: 'bg-danger text-white',
            info: 'bg-info text-white',
            warning: 'bg-warning text-dark'
        },
        icons: {
            success: 'fas fa-check',
            error: 'fas fa-times',
            info: 'fas fa-info',
            warning: 'fas fa-exclamation-triangle'
        },
        timeouts: {
            success: 2000,
            error: 3000,
            info: 2000,
            warning: 2000
        },
        baseClasses: 'rounded px-2 py-1 shadow-sm',
        baseStyles: {
            fontSize: '0.75rem',
            cursor: 'pointer',
            animation: 'fadeInUp 0.3s ease-out',
            userSelect: 'none'
        }
    };

    static showMessage(message, type, container, options = {}) {
        const config = { ...this.DEFAULT_CONFIG, ...options };

        if (typeof container === 'string') {
            container = document.querySelector(container);
        }

        if (!container) {
            console.log(`${type.toUpperCase()}: ${message}`);
            return null;
        }

        container.innerHTML = '';
        const messageEl = this.createMessageElement(message, type, config);
        container.appendChild(messageEl);

        const timeout = config.timeouts[type] || config.timeouts.info;
        setTimeout(() => this.removeMessage(messageEl), timeout);

        messageEl.addEventListener('click', () => this.removeMessage(messageEl));

        return messageEl;
    }

    static createMessageElement(message, type, config = {}) {
        const finalConfig = { ...this.DEFAULT_CONFIG, ...config };
        const messageEl = document.createElement('div');

        const alertClass = finalConfig.alertClasses[type] || finalConfig.alertClasses.info;
        const icon = finalConfig.icons[type] || finalConfig.icons.info;

        messageEl.className = `${alertClass} ${finalConfig.baseClasses}`;

        Object.assign(messageEl.style, finalConfig.baseStyles);

        if (finalConfig.additionalStyles) {
            Object.assign(messageEl.style, finalConfig.additionalStyles);
        }

        messageEl.innerHTML = `<i class="${icon} me-1"></i>${message}`;
        return messageEl;
    }

    static removeMessage(messageEl) {
        if (!messageEl || !messageEl.parentNode) return;

        messageEl.style.animation = 'fadeOutUp 0.3s ease-in';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }

    static showGlobalMessage(message, type = 'info', options = {}) {
        const messagesContainer = document.querySelector('.messages-container, #messages');
        if (!messagesContainer) {
            console.warn('Global message container not found. Message:', message);
            return null;
        }

        const typeMap = {
            warning: { alertClass: 'alert-warning', iconClass: 'fas fa-exclamation-circle fa-lg', title: 'Warning:' },
            error: { alertClass: 'alert-danger', iconClass: 'fas fa-exclamation-triangle fa-lg', title: 'Error:' },
            success: { alertClass: 'alert-success', iconClass: 'fas fa-check-circle fa-lg', title: 'Success:' },
            info: { alertClass: 'alert-info', iconClass: 'fas fa-info-circle fa-lg', title: 'Info:' }
        };
        const config = typeMap[type] || typeMap.info;
        const timeout = options.timeout || 10000;

        const alertEl = document.createElement('div');
        alertEl.className = `alert ${config.alertClass} alert-dismissible fade show message-alert`;
        alertEl.setAttribute('role', 'alert');

        const transitionDuration = timeout / 1000;
        alertEl.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="me-3"><i class="${config.iconClass}"></i></div>
                <div class="flex-grow-1">
                    <strong>${config.title}</strong>
                    ${this.escapeHtml(message)}
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            <div class="progress mt-2" style="height: 3px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     role="progressbar"
                     style="width: 100%; transition: width ${transitionDuration}s linear;">
                </div>
            </div>
        `;
        messagesContainer.appendChild(alertEl);

        const progressBar = alertEl.querySelector('.progress-bar');
        setTimeout(() => {
            if (progressBar) progressBar.style.width = '0%';
        }, 100);

        let autoCloseTimer = setTimeout(() => {
            MessageManager.closeGlobalMessage(alertEl);
        }, timeout);

        alertEl.addEventListener('mouseenter', () => {
            clearTimeout(autoCloseTimer);
            if (progressBar) progressBar.style.animationPlayState = 'paused';
        });

        alertEl.addEventListener('mouseleave', () => {
            if (progressBar) progressBar.style.animationPlayState = 'running';
            autoCloseTimer = setTimeout(() => {
                MessageManager.closeGlobalMessage(alertEl);
            }, 2000);
        });

        const closeButton = alertEl.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                clearTimeout(autoCloseTimer);
                MessageManager.closeGlobalMessage(alertEl);
            });
        }
        return alertEl;
    }

    static closeGlobalMessage(alert) {
        if (!alert) return;
        alert.classList.add('fade-out');
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 500);
    }

    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    static RATING_CONFIG = {
        alertClasses: {
            success: 'bg-success',
            error: 'bg-danger',
            info: 'bg-info',
            warning: 'bg-warning'
        },
        baseClasses: '',
        baseStyles: {
            cursor: 'pointer',
            userSelect: 'none',
            animation: 'fadeInUp .2s ease-out'
        }
    };

    static LIKES_CONFIG = {
        baseStyles: {
            fontSize: '0.75rem',
            cursor: 'pointer',
            animation: 'fadeInUp 0.3s ease-out',
            whiteSpace: 'nowrap',
            userSelect: 'none'
        }
    };
}
