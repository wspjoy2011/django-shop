import {getCookie, isLoginRedirectResponse, isLoginRedirectErrorLike} from '../utils/httpAuth.js';

class FavoriteButtonHandler {
    constructor() {
        this.selectors = {
            component: '.favorite-component',
            button: '.favorite-btn',
            icon: '.favorite-icon',
            count: '.favorite-count',
            messages: '.favorite-messages-container'
        };

        this.cssClasses = {
            favorited: 'favorited-active',
            loading: 'loading',
            disabled: 'disabled'
        };

        this.init();
    }

    init() {
        this.setupCSRF();
        this.setupBroadcastChannel();
        this.bindEvents();
        this.bootstrapInitialState();
    }

    setupCSRF() {
        this.csrfToken = getCookie('csrftoken');
    }

    setupBroadcastChannel() {
        if (typeof BroadcastChannel !== 'undefined') {
            this.broadcastChannel = new BroadcastChannel('favorite-updates');
            this.broadcastChannel.addEventListener('message', (event) => {
                this.handleBroadcastMessage(event.data);
            });
        }
    }

    handleBroadcastMessage(data) {
        if (!data || !data.type) return;

        switch (data.type) {
            case 'favorite_updated':
                this.handleFavoriteUpdateMessage(data);
                break;
            case 'logout_detected':
                this.handleLogoutMessage(data);
                break;
        }
    }

    handleFavoriteUpdateMessage(data) {
        const { productId, action, favoritesCount } = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            this.updateFavoriteState(comp, action === 'added', favoritesCount);
        });
    }

    handleLogoutMessage(data) {
        const { productId } = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            comp.dataset.authenticated = 'false';
            comp.dataset.inFavorites = 'false';
            comp.classList.remove(this.cssClasses.favorited);
            this.updateUI(comp, false, comp.querySelector(this.selectors.count)?.textContent || 0);
        });
    }

    findComponentsForUpdate(productId) {
        if (!productId) return [];
        return Array.from(document.querySelectorAll(this.selectors.component))
            .filter(component => component.dataset.productId === productId);
    }

    broadcastFavoriteUpdate(component, action, favoritesCount) {
        if (!this.broadcastChannel) return;

        const message = {
            type: 'favorite_updated',
            productId: component.dataset.productId,
            action: action,
            favoritesCount: favoritesCount,
            timestamp: Date.now()
        };

        this.broadcastChannel.postMessage(message);
    }

    broadcastLogoutDetection(component) {
        if (!this.broadcastChannel) return;

        const message = {
            type: 'logout_detected',
            productId: component.dataset.productId,
            timestamp: Date.now()
        };

        this.broadcastChannel.postMessage(message);
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest(this.selectors.button);
            if (button) {
                const component = button.closest(this.selectors.component);
                if (!component) return;
                e.preventDefault();
                void this.onFavoriteClick(component);
            }
        });

        window.addEventListener('beforeunload', () => {
            if (this.broadcastChannel) {
                this.broadcastChannel.close();
            }
        });
    }

    bootstrapInitialState() {
        document.querySelectorAll(this.selectors.component).forEach((comp) => {
            const inFavorites = comp.dataset.inFavorites === 'true';
            this.updateFavoriteState(comp, inFavorites);
        });
    }

    async onFavoriteClick(component) {
        if (!this.isAuthenticated(component)) {
            this.showMessage('Login required', 'info', component);
            return;
        }

        if (this.isLoading(component)) return;

        const url = component.dataset.favoriteUrl;

        try {
            this.setLoadingState(component, true);
            const response = await this.sendRequest(url);

            if (isLoginRedirectResponse(response)) {
                this.handleLogoutDetection(component, response.url);
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const inFavorites = data.action === 'added';

            const componentsToUpdate = this.findComponentsForUpdate(component.dataset.productId);
            componentsToUpdate.forEach(comp => {
                this.updateFavoriteState(comp, inFavorites, data.favorites_count);
            });

            this.broadcastFavoriteUpdate(component, data.action, data.favorites_count);

            const message = data.action === 'added' ? '❤️ Added to favorites!' : 'Removed from favorites';
            this.showMessage(message, 'success', component);

        } catch (error) {
            console.error('Favorite toggle error:', error);
            if (isLoginRedirectErrorLike(error)) {
                this.handleLogoutDetection(component);
            } else {
                this.showError('Failed to update favorites. Please try again.', component);
            }
        } finally {
            this.setLoadingState(component, false);
        }
    }

    updateFavoriteState(component, inFavorites, count = null) {
        component.dataset.inFavorites = inFavorites ? 'true' : 'false';

        component.classList.toggle(this.cssClasses.favorited, inFavorites);

        this.updateUI(component, inFavorites, count);
    }

    updateUI(component, inFavorites, count = null) {
        const icon = component.querySelector(this.selectors.icon);
        if (icon) {
            icon.className = `${inFavorites ? 'fas' : 'far'} fa-heart favorite-icon`;
        }

        if (count !== null) {
            const countEl = component.querySelector(this.selectors.count);
            if (countEl) {
                countEl.textContent = count;
            }
        }

        const button = component.querySelector(this.selectors.button);
        if (button) {
            const title = inFavorites ? 'Remove from favorites' : 'Add to favorites';
            button.setAttribute('title', title);
        }
    }

    setLoadingState(component, isLoading) {
        const button = component.querySelector(this.selectors.button);
        if (!button) return;

        if (isLoading) {
            button.classList.add(this.cssClasses.disabled);
            button.disabled = true;
        } else {
            button.classList.remove(this.cssClasses.disabled);
            button.disabled = false;
        }
    }

    isLoading(component) {
        const button = component.querySelector(this.selectors.button);
        return button && button.classList.contains(this.cssClasses.disabled);
    }

    handleLogoutDetection(component, loginUrl = null) {
        const componentsToUpdate = this.findComponentsForUpdate(component.dataset.productId);

        componentsToUpdate.forEach(comp => {
            comp.dataset.authenticated = 'false';
            comp.dataset.inFavorites = 'false';
            comp.classList.remove(this.cssClasses.favorited);
            this.updateUI(comp, false);
        });

        this.broadcastLogoutDetection(component);

        const message = 'Session expired.';
        this.showMessage(message, 'warning', component);
    }

    async sendRequest(url) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json',
            }
        });
    }

    isAuthenticated(component) {
        return component.dataset.authenticated === 'true';
    }

    showError(message, component) {
        this.showMessage(message, 'error', component);
    }

    showMessage(message, type, component) {
        const container = component.querySelector(this.selectors.messages);
        if (!container) {
            console.log(`${type.toUpperCase()}: ${message}`);
            return;
        }

        container.innerHTML = '';
        const messageEl = this.createMessageElement(message, type);
        container.appendChild(messageEl);
        setTimeout(() => this.removeMessage(messageEl), type === 'error' ? 3000 : 2000);
        messageEl.addEventListener('click', () => this.removeMessage(messageEl));
    }

    createMessageElement(message, type) {
        const messageEl = document.createElement('div');

        const alertClasses = {
            success: 'bg-success text-white',
            error: 'bg-danger text-white',
            info: 'bg-info text-white',
            warning: 'bg-warning text-dark'
        };
        const alertClass = alertClasses[type] || 'bg-info text-white';

        messageEl.className = `${alertClass} rounded px-2 py-1 shadow-sm`;
        messageEl.style.fontSize = '0.75rem';
        messageEl.style.cursor = 'pointer';
        messageEl.style.animation = 'fadeInUp 0.3s ease-out';
        messageEl.style.userSelect = 'none';

        const icons = {
            success: 'fas fa-check',
            error: 'fas fa-times',
            info: 'fas fa-info',
            warning: 'fas fa-exclamation'
        };
        const icon = icons[type] || icons.info;

        messageEl.innerHTML = `<i class="${icon} me-1"></i>${message}`;
        return messageEl;
    }

    removeMessage(messageEl) {
        if (!messageEl || !messageEl.parentNode) return;
        messageEl.style.animation = 'fadeOutUp 0.3s ease-in';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 300);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FavoriteButtonHandler();
});
