import {ComponentFinder} from '../utils/broadcastManager.js';
import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {LoadingStateManager} from '../utils/components/LoadingStateManager.js';

class LikesDislikesHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'likes-dislikes-updates'});

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

        this.httpClient = new AuthenticatedHttpClient();
        this.init();
    }

    init() {
        super.init();
        this.setupAuthUI();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('like_dislike_updated', (data) => {
            this.handleLikeDislikeUpdateMessage(data);
        });
    }

    setupAuthBroadcastSubscriptions() {
        this.authBroadcastManager.subscribe('logout_detected', (data) => {
            this.handleLogoutMessage(data);
        });
    }

    handleLikeDislikeUpdateMessage(data) {
        const {productId, action, likesCount, dislikesCount} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            this.updateCounts(comp, likesCount, dislikesCount);
            this.updateButtonStates(comp, action, data.type === 'like' ? 'like' : 'dislike');
        });
    }

    handleLogoutMessage(data) {
        const allComponents = document.querySelectorAll(this.selectors.component);
        allComponents.forEach(comp => {
            this.applyUnauthenticatedState(comp);
        });
    }

    applyUnauthenticatedState(component) {
        AuthenticationHandler.applyUnauthenticatedState(component, {
            cssClasses: this.cssClasses,
            selectors: {buttons: `${this.selectors.likeButton}, ${this.selectors.dislikeButton}`},
            resetCallback: (comp) => {
                this.resetSelectionState(comp);
                this.ensureAuthHintTitles(comp);
            }
        });
    }

    findComponentsForUpdate(productId) {
        if (productId && productId.trim()) {
            return ComponentFinder.findByProductId(productId, this.selectors.component);
        } else {
            return [];
        }
    }

    broadcastLikeDislikeUpdate(component, action, likesCount, dislikesCount, type) {
        this.broadcastManager.broadcast('like_dislike_updated', {
            productId: component.dataset.productId,
            action: action,
            likesCount: likesCount,
            dislikesCount: dislikesCount,
            interactionType: type
        });
    }

    setupAuthUI() {
        document.querySelectorAll(this.selectors.component).forEach(component => {
            const isAuthenticated = AuthenticationHandler.validateAuthentication(component);
            const buttons = component.querySelectorAll(
                `${this.selectors.likeButton}, ${this.selectors.dislikeButton}`
            );

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
        super.bindEvents();

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
    }

    async handleLikeClick(likeButton) {
        const component = likeButton.closest(this.selectors.component);

        if (!AuthenticationHandler.validateAuthentication(component)) {
            this.showAuthenticationMessage(component);
            return;
        }
        if (LoadingStateManager.isLoading(component, {cssClass: this.cssClasses.disabled})) return;

        const url = component.dataset.likeUrl;
        await this.toggleRating(component, url, 'like');
    }

    async handleDislikeClick(dislikeButton) {
        const component = dislikeButton.closest(this.selectors.component);

        if (!AuthenticationHandler.validateAuthentication(component)) {
            this.showAuthenticationMessage(component);
            return;
        }
        if (LoadingStateManager.isLoading(component, {cssClass: this.cssClasses.disabled})) return;

        const url = component.dataset.dislikeUrl;
        await this.toggleRating(component, url, 'dislike');
    }

    async toggleRating(component, url, type) {
        try {
            this.setLoadingState(component, true);

            const result = await this.httpClient.handleResponse(
                await this.httpClient.sendRequest(url),
                component,
                {
                    onLoginRedirect: (loginUrl) => this.handleLogoutDetection(component, loginUrl),
                    onSuccess: (data) => {
                        this.updateUI(component, data, type);
                        this.broadcastLikeDislikeUpdate(
                            component,
                            data.action,
                            data.likes_count,
                            data.dislikes_count,
                            type)
                        ;
                        this.showFeedback(data.action, type, component);
                    },
                    onError: (error) => {
                        MessageManager.showMessage(
                            'Failed to update rating. Please try again.',
                            'error',
                            component.querySelector(this.selectors.messageContainer),
                            MessageManager.LIKES_CONFIG
                        );
                    }
                }
            );

        } catch (error) {
            console.error('Rating toggle error:', error);
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection(component);
            } else {
                MessageManager.showMessage(
                    'Failed to update rating. Please try again.',
                    'error',
                    component.querySelector(this.selectors.messageContainer),
                    MessageManager.LIKES_CONFIG
                );
            }
        } finally {
            this.setLoadingState(component, false);
        }
    }

    handleLogoutDetection() {
        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager);
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

        ComponentFinder.findByProductId(productId, this.selectors.component).forEach(comp => {
            this.updateCounts(comp, data.likes_count, data.dislikes_count);
            this.updateButtonStates(comp, data.action, type);

            if (comp === component) {
                this.animateButton(comp, type);
            }
        });
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
        LoadingStateManager.setLoadingState(component, isLoading, {
            selectors: {buttons: `${this.selectors.likeButton}, ${this.selectors.dislikeButton}`},
            cssClasses: {disabled: this.cssClasses.disabled},
            disablePointerEvents: true
        });
    }

    showAuthenticationMessage(component) {
        MessageManager.showMessage(
            'Login required',
            'info',
            component.querySelector(this.selectors.messageContainer),
            MessageManager.LIKES_CONFIG
        );
    }

    showFeedback(action, type, component) {
        const messages = {
            liked: '❤️ Liked!',
            unliked: 'Like removed',
            disliked: '👎 Disliked!',
            undisliked: 'Dislike removed'
        };
        MessageManager.showMessage(
            messages[action] || `${action} successful`,
            'success', component.querySelector(this.selectors.messageContainer),
            MessageManager.LIKES_CONFIG
        );
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
