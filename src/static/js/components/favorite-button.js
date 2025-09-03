import { ComponentFinder } from '../utils/broadcastManager.js';
import { BaseComponent } from '../utils/components/BaseComponent.js';
import { MessageManager } from '../utils/components/MessageManager.js';
import { AuthenticationHandler } from '../utils/components/AuthenticationHandler.js';
import { AuthenticatedHttpClient } from '../utils/http/AuthenticatedHttpClient.js';
import { LoadingStateManager } from '../utils/components/LoadingStateManager.js';

class FavoriteButtonHandler extends BaseComponent {
    constructor() {
        super({ broadcastChannelName: 'favorite-updates' });
        
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

        this.httpClient = new AuthenticatedHttpClient();
        this.init();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('favorite_updated', (data) => {
            this.handleFavoriteUpdateMessage(data);
        });

        this.broadcastManager.subscribe('logout_detected', (data) => {
            this.handleLogoutMessage(data);
        });
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
            AuthenticationHandler.resetAuthenticationState(comp, (component) => {
                component.dataset.inFavorites = 'false';
                component.classList.remove(this.cssClasses.favorited);
                this.updateUI(component, false, component.querySelector(this.selectors.count)?.textContent || 0);
            });
        });
    }

    findComponentsForUpdate(productId) {
        if (productId && productId.trim()) {
            return ComponentFinder.findByProductId(productId, this.selectors.component);
        } else {
            return [];
        }
    }

    broadcastFavoriteUpdate(component, action, favoritesCount) {
        this.broadcastManager.broadcast('favorite_updated', {
            productId: component.dataset.productId,
            action: action,
            favoritesCount: favoritesCount
        });
    }

    bindEvents() {
        super.bindEvents();

        document.addEventListener('click', (e) => {
            const button = e.target.closest(this.selectors.button);
            if (button) {
                const component = button.closest(this.selectors.component);
                if (!component) return;
                e.preventDefault();
                void this.onFavoriteClick(component);
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
            MessageManager.showMessage('Login required', 'info', component.querySelector(this.selectors.messages));
            return;
        }

        if (LoadingStateManager.isLoading(component, { selector: this.selectors.button, cssClass: this.cssClasses.disabled })) {
            return;
        }

        const url = component.dataset.favoriteUrl;

        try {
            this.setLoadingState(component, true);
            
            const result = await this.httpClient.handleResponse(
                await this.httpClient.sendRequest(url),
                component,
                {
                    onLoginRedirect: (loginUrl) => this.handleLogoutDetection(component, loginUrl),
                    onSuccess: (data) => this.handleSuccessResponse(component, data),
                    onError: (error) => this.handleErrorResponse(error, component)
                }
            );

        } catch (error) {
            console.error('Favorite toggle error:', error);
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection(component);
            } else {
                MessageManager.showMessage('Failed to update favorites. Please try again.', 'error', component.querySelector(this.selectors.messages));
            }
        } finally {
            this.setLoadingState(component, false);
        }
    }

    handleSuccessResponse(component, data) {
        const inFavorites = data.action === 'added';
        const componentsToUpdate = this.findComponentsForUpdate(component.dataset.productId);
        
        componentsToUpdate.forEach(comp => {
            this.updateFavoriteState(comp, inFavorites, data.favorites_count);
        });

        this.broadcastFavoriteUpdate(component, data.action, data.favorites_count);

        const message = data.action === 'added' ? '❤️ Added to favorites!' : 'Removed from favorites';
        MessageManager.showMessage(message, 'success', component.querySelector(this.selectors.messages));
    }

    handleErrorResponse(error, component) {
        MessageManager.showMessage('Failed to update favorites. Please try again.', 'error', component.querySelector(this.selectors.messages));
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
        LoadingStateManager.setLoadingState(component, isLoading, {
            selectors: { button: this.selectors.button },
            cssClasses: { disabled: this.cssClasses.disabled }
        });
    }

    handleLogoutDetection(component, loginUrl = null) {
        AuthenticationHandler.handleLogoutDetection(component, this.broadcastManager, {
            loginUrl,
            messageManager: MessageManager,
            messageContainer: component.querySelector(this.selectors.messages),
            productIdGetter: (comp, forBroadcast = false) => {
                if (forBroadcast) {
                    return { productId: comp.dataset.productId };
                }
                return this.findComponentsForUpdate(comp.dataset.productId);
            },
            resetCallback: (comp) => {
                comp.dataset.inFavorites = 'false';
                comp.classList.remove(this.cssClasses.favorited);
                this.updateUI(comp, false);
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FavoriteButtonHandler();
});
