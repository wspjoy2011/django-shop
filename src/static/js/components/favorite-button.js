import {ComponentFinder} from '../utils/broadcastManager.js';
import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {LoadingStateManager} from '../utils/components/LoadingStateManager.js';

class FavoriteButtonHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'favorite-updates'});

        this.selectors = {
            component: '.favorite-component',
            button: '.favorite-btn',
            icon: '.favorite-star',
            count: '.favorite-count',
            messages: '.favorite-messages-container',
            container: '.favorite-container'
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
    }

    setupAuthBroadcastSubscriptions() {
        this.authBroadcastManager.subscribe('logout_detected', () => {
            this.handleLogoutMessage();
        });
    }

    handleFavoriteUpdateMessage(data) {
        const {productId, action, favoritesCount} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId);

        componentsToUpdate.forEach(comp => {
            this.updateFavoriteState(comp, action === 'added', favoritesCount);
        });
    }

    handleLogoutMessage() {
        const allComponents = document.querySelectorAll(this.selectors.component);
        allComponents.forEach(component => {
            AuthenticationHandler.resetAuthenticationState(
                component,
                (comp) => this.resetComponentOnLogout(comp)
            );
        });
    }

    resetComponentOnLogout(component) {
        component.classList.remove(this.cssClasses.favorited);

        component.dataset.inFavorites = 'false';

        const container = component.querySelector(this.selectors.container);
        const button = component.querySelector(this.selectors.button);
        const title = 'Login to add to favorites';

        if (container) container.setAttribute('title', title);
        if (button) button.setAttribute('title', title);
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
            MessageManager.showMessage(
                'Login required', 'info',
                component.querySelector(this.selectors.messages)
            );
            return;
        }

        if (LoadingStateManager.isLoading(component, {
            selector: this.selectors.button,
            cssClass: this.cssClasses.disabled
        })) {
            return;
        }

        const url = component.dataset.favoriteUrl;

        try {
            this.setLoadingState(component, true);

            await this.httpClient.handleResponse(
                await this.httpClient.sendRequest(url),
                component,
                {
                    onLoginRedirect: (loginUrl) => this.handleLogoutDetection(component, loginUrl),
                    onSuccess: (data) => this.handleSuccessResponse(component, data),
                    onError: (error) => this.handleErrorResponse(error, component)
                }
            );

        } catch (error) {
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection(component);
            } else {
                MessageManager.showMessage(
                    'Failed to update favorites. Please try again.',
                    'error',
                    component.querySelector(this.selectors.messages)
                );
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
        MessageManager.showMessage(
            'Failed to update favorites. Please try again.',
            'error',
            component.querySelector(this.selectors.messages)
        );
    }

    updateFavoriteState(component, inFavorites, count = null) {
        component.dataset.inFavorites = inFavorites ? 'true' : 'false';
        component.classList.toggle(this.cssClasses.favorited, inFavorites);
        this.updateUI(component, inFavorites, count);
    }

    updateUI(component, inFavorites, count = null) {
        if (count !== null) {
            const countEl = component.querySelector(this.selectors.count);
            if (countEl) {
                countEl.textContent = count;
            }
        }

        const button = component.querySelector(this.selectors.button);
        const container = component.querySelector(this.selectors.container);

        let title;
        if (!this.isAuthenticated(component)) {
            title = 'Login to add to favorites';
        } else {
            title = inFavorites ? 'Remove from favorites' : 'Add to favorites';
        }

        if (button) button.setAttribute('title', title);
        if (container) container.setAttribute('title', title);
    }

    setLoadingState(component, isLoading) {
        LoadingStateManager.setLoadingState(component, isLoading, {
            selectors: {button: this.selectors.button},
            cssClasses: {disabled: this.cssClasses.disabled}
        });
    }

    handleLogoutDetection() {
        this.handleLogoutMessage();
        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FavoriteButtonHandler();
});
