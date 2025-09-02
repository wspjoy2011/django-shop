import {getCookie, isLoginRedirectResponse, isLoginRedirectErrorLike} from '../utils/httpAuth.js'

class LikesDislikesHandler {
    constructor() {
        this.selectors = {
            component: '.likes-dislikes-component',
            likeButton: '.likes-item',
            dislikeButton: '.dislikes-item',
            likeCount: '.likes-count',
            dislikeCount: '.dislikes-count',
            likeIcon: '.likes-icon',
            dislikeIcon: '.dislikes-icon',
            messageContainer: '.likes-messages-container'
        };

        this.cssClasses = {
            loading: 'loading',
            likedActive: 'liked-active',
            likedInactive: 'liked-inactive',
            dislikedActive: 'disliked-active',
            dislikedInactive: 'disliked-inactive',
            disabled: 'disabled',
            unauthenticated: 'unauthenticated'
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.setupCSRF();
        this.setupBroadcastChannel();
        this.setupAuthUI();
    }

    setupCSRF() {
        this.csrfToken = getCookie('csrftoken');
    }

    setupBroadcastChannel() {
        if (typeof BroadcastChannel !== 'undefined') {
            this.broadcastChannel = new BroadcastChannel('likes-dislikes-updates');
            this.broadcastChannel.addEventListener('message', (event) => {
                this.handleBroadcastMessage(event.data);
            });
        }
    }

    handleBroadcastMessage(data) {
        if (!data || !data.type) return;

        switch (data.type) {
            case 'like_dislike_updated':
                this.handleLikeDislikeUpdateMessage(data);
                break;
            case 'logout_detected':
                this.handleLogoutMessage(data);
                break;
        }
    }

    handleLikeDislikeUpdateMessage(data) {
        const {productId, action, likesCount, dislikesCount} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            this.updateCounts(comp, likesCount, dislikesCount);
            this.updateButtonStates(comp, action, data.type === 'like' ? 'like' : 'dislike');
        });
    }

    applyUnauthenticatedState(component) {
        component.dataset.authenticated = 'false';
        component.classList.add(this.cssClasses.unauthenticated);

        const buttons = component.querySelectorAll(`${this.selectors.likeButton}, ${this.selectors.dislikeButton}`);
        buttons.forEach(b => (b.style.cursor = 'default'));

        this.resetSelectionState(component);
        this.ensureAuthHintTitles(component);
    }

    handleLogoutMessage(data) {
        const {productId} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            this.applyUnauthenticatedState(comp);
        });
    }

    findComponentsForUpdate(productId) {
        if (productId && productId.trim()) {
            return this.getSameProductComponents(productId);
        } else {
            return [];
        }
    }

    broadcastLikeDislikeUpdate(component, action, likesCount, dislikesCount, type) {
        if (!this.broadcastChannel) return;

        const message = {
            type: 'like_dislike_updated',
            productId: component.dataset.productId,
            action: action,
            likesCount: likesCount,
            dislikesCount: dislikesCount,
            interactionType: type,
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

    setupAuthUI() {
        document.querySelectorAll(this.selectors.component).forEach(component => {
            const isAuthenticated = this.validateAuthentication(component);
            const buttons = component.querySelectorAll(`${this.selectors.likeButton}, ${this.selectors.dislikeButton}`);

            if (!isAuthenticated) {
                component.classList.add(this.cssClasses.unauthenticated);
                buttons.forEach(b => (b.style.cursor = 'default'));
                buttons.forEach(b => {
                    const title = b.getAttribute('title');
                    if (!title || title.trim() === '') b.removeAttribute('title');
                });
            } else {
                buttons.forEach(b => b.removeAttribute('title'));
            }
        });
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            const likeButton = e.target.closest(this.selectors.likeButton);
            const dislikeButton = e.target.closest(this.selectors.dislikeButton);

            if (likeButton) {
                e.preventDefault();
                void this.handleLikeClick(likeButton);
            } else if (dislikeButton) {
                e.preventDefault();
                void this.handleDislikeClick(dislikeButton);
            }
        });

        window.addEventListener('beforeunload', () => {
            if (this.broadcastChannel) {
                this.broadcastChannel.close();
            }
        });
    }

    async handleLikeClick(likeButton) {
        const component = likeButton.closest(this.selectors.component);

        if (!this.validateAuthentication(component)) {
            this.showAuthenticationMessage(component);
            return;
        }
        if (this.isLoading(component)) return;

        const url = component.dataset.likeUrl;
        await this.toggleRating(component, url, 'like');
    }

    async handleDislikeClick(dislikeButton) {
        const component = dislikeButton.closest(this.selectors.component);

        if (!this.validateAuthentication(component)) {
            this.showAuthenticationMessage(component);
            return;
        }
        if (this.isLoading(component)) return;

        const url = component.dataset.dislikeUrl;
        await this.toggleRating(component, url, 'dislike');
    }

    async toggleRating(component, url, type) {
        try {
            this.setLoadingState(component, true);

            const response = await this.sendRequest(url);

            if (isLoginRedirectResponse(response)) {
                this.handleLogoutDetection(component, response.url);
                return;
            }

            if (response.ok) {
                const data = await response.json();
                this.updateUI(component, data, type);

                this.broadcastLikeDislikeUpdate(component, data.action, data.likes_count, data.dislikes_count, type);

                this.showFeedback(data.action, type, component);
            } else {
                try {
                    const text = await response.text();
                    console.warn('Server response (non-OK):', text?.slice(0, 300));
                } catch (_) {
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Rating toggle error:', error);
            if (isLoginRedirectErrorLike(error)) {
                this.handleLogoutDetection(component);
            } else {
                this.showError('Failed to update rating. Please try again.', component);
            }
        } finally {
            this.setLoadingState(component, false);
        }
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

    handleLogoutDetection(component, loginUrl = null) {
        const productId = component.dataset.productId;

        this.getSameProductComponents(productId).forEach(comp => {
            this.applyUnauthenticatedState(comp);
        });

        this.broadcastLogoutDetection(component);

        const message = loginUrl
            ? `Session expired.`
            : `Session expired.`;
        this.showMessage(message, 'info', component);
    }

    ensureAuthHintTitles(component) {
        const likeBtn = component.querySelector(this.selectors.likeButton);
        const dislikeBtn = component.querySelector(this.selectors.dislikeButton);

        if (likeBtn && !likeBtn.getAttribute('title')) {
            likeBtn.setAttribute('title', 'Login to like products');
        }
        if (dislikeBtn && !dislikeBtn.getAttribute('title')) {
            dislikeBtn.setAttribute('title', 'Login to dislike products');
        }
    }

    updateUI(component, data, type) {
        const productId = component.dataset.productId;

        this.getSameProductComponents(productId).forEach(comp => {
            this.updateCounts(comp, data.likes_count, data.dislikes_count);
            this.updateButtonStates(comp, data.action, type);

            if (comp === component) {
                this.animateButton(comp, type);
            }
        });

        this.showFeedback(data.action, type, component);
    }

    getSameProductComponents(productId) {
        if (!productId) return [];

        return Array.from(document.querySelectorAll(this.selectors.component))
            .filter(component => component.dataset.productId === productId);
    }

    updateCounts(component, likesCount, dislikesCount) {
        const likeCountEl = component.querySelector(this.selectors.likeCount);
        const dislikeCountEl = component.querySelector(this.selectors.dislikeCount);
        if (likeCountEl) likeCountEl.textContent = likesCount;
        if (dislikeCountEl) dislikeCountEl.textContent = dislikesCount;
    }

    updateButtonStates(component, action, type) {
        const likeButton = component.querySelector(this.selectors.likeButton);
        const dislikeButton = component.querySelector(this.selectors.dislikeButton);

        likeButton?.classList.remove(this.cssClasses.likedActive, this.cssClasses.likedInactive);
        dislikeButton?.classList.remove(this.cssClasses.dislikedActive, this.cssClasses.dislikedInactive);

        if (action === 'liked') {
            likeButton?.classList.add(this.cssClasses.likedActive);
            dislikeButton?.classList.add(this.cssClasses.dislikedInactive);
        } else if (action === 'unliked') {
            likeButton?.classList.add(this.cssClasses.likedInactive);
            dislikeButton?.classList.add(this.cssClasses.dislikedInactive);
        } else if (action === 'disliked') {
            likeButton?.classList.add(this.cssClasses.likedInactive);
            dislikeButton?.classList.add(this.cssClasses.dislikedActive);
        } else if (action === 'undisliked') {
            likeButton?.classList.add(this.cssClasses.likedInactive);
            dislikeButton?.classList.add(this.cssClasses.dislikedInactive);
        }
    }

    animateButton(component, type) {
        const selector = type === 'like' ? this.selectors.likeIcon : this.selectors.dislikeIcon;
        const icon = component.querySelector(selector);
        if (!icon) return;

        icon.style.transform = 'scale(1.2)';
        setTimeout(() => {
            icon.style.transform = '';
        }, 150);
    }

    setLoadingState(component, isLoading) {
        const buttons = component.querySelectorAll(`${this.selectors.likeButton}, ${this.selectors.dislikeButton}`);
        buttons.forEach(button => {
            if (isLoading) {
                button.classList.add(this.cssClasses.disabled);
                button.style.pointerEvents = 'none';
            } else {
                button.classList.remove(this.cssClasses.disabled);
                button.style.pointerEvents = '';
            }
        });
    }

    isLoading(component) {
        return component.querySelector(`.${this.cssClasses.disabled}`) !== null;
    }

    validateAuthentication(component) {
        return component.dataset.authenticated === 'true';
    }

    showAuthenticationMessage(component) {
        this.showMessage('Login required', 'info', component);
    }

    showFeedback(action, type, component) {
        const messages = {
            liked: '❤️ Liked!',
            unliked: 'Like removed',
            disliked: '👎 Disliked!',
            undisliked: 'Dislike removed'
        };
        this.showMessage(messages[action] || `${action} successful`, 'success', component);
    }

    showError(message, component) {
        this.showMessage(message, 'error', component);
    }

    showMessage(message, type, component) {
        const container = component.querySelector(this.selectors.messageContainer);
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
        messageEl.style.whiteSpace = 'nowrap';
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

    resetSelectionState(component) {
        const likeBtn = component.querySelector(this.selectors.likeButton);
        const dislikeBtn = component.querySelector(this.selectors.dislikeButton);

        if (likeBtn) {
            likeBtn.classList.remove(this.cssClasses.likedActive, 'user-liked');
            likeBtn.classList.add(this.cssClasses.likedInactive);
            likeBtn.setAttribute('title', 'Login to like products');
        }
        if (dislikeBtn) {
            dislikeBtn.classList.remove(this.cssClasses.dislikedActive, 'user-disliked');
            dislikeBtn.classList.add(this.cssClasses.dislikedInactive);
            dislikeBtn.setAttribute('title', 'Login to dislike products');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new LikesDislikesHandler();
});
