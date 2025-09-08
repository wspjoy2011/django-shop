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
        const messagesContainer = document.querySelector('.messages-container') ||
            document.querySelector('#messages') ||
            document.querySelector('.alert-container');

        if (messagesContainer) {
            const alertClass = type === 'warning' ? 'alert-warning' :
                type === 'error' ? 'alert-danger' : 'alert-info';

            const messageElement = document.createElement('div');
            messageElement.className = `alert ${alertClass} alert-dismissible fade show`;
            messageElement.innerHTML = `
                ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            messagesContainer.appendChild(messageElement);

            const timeout = options.timeout || 5000;
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.remove();
                }
            }, timeout);

            return messageElement;
        } else {
            console.warn('Global message:', message);
            return null;
        }
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
