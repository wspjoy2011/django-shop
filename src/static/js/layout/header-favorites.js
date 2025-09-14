import { BaseComponent } from '../utils/components/BaseComponent.js';
import { AuthenticatedHttpClient } from '../utils/http/AuthenticatedHttpClient.js';
import { BroadcastManager } from '../utils/broadcastManager.js';

class HeaderFavoritesHandler extends BaseComponent {
    constructor() {
        super({ broadcastChannelName: 'favorite-updates' });

        this.selectors = {
            container: '.favorites-heart-container',
            heart: '.favorites-heart-filled, .favorites-heart-empty',
            bubble: '.favorites-count-bubble'
        };

        this.countUrl = '/api/v1/favorites/collections/count/';
        this.httpClient = new AuthenticatedHttpClient();
        this.collectionUpdatesManager = BroadcastManager.createManager('collection-updates');
        this.init();
    }

    bootstrapInitialState() {
        const container = document.querySelector(this.selectors.container);
        if (container) {
            void this.fetchAndUpdateCount();
        }
    }

    setupBroadcastSubscriptions() {
        const updateHandler = () => this.fetchAndUpdateCount();
        this.broadcastManager.subscribe('favorite_updated', updateHandler);
        this.collectionUpdatesManager.subscribe('collection_deleted', updateHandler);
        this.collectionUpdatesManager.subscribe('collection_updated', updateHandler);
    }

    setupAuthBroadcastSubscriptions() {
        this.authBroadcastManager.subscribe('logout_detected', this.handleLogout.bind(this));
    }

    async fetchAndUpdateCount() {
        const container = document.querySelector(this.selectors.container);
        if (!container) return;

        try {
            const response = await this.httpClient.sendRequest(this.countUrl, { method: 'GET' });
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    this.handleLogout();
                }
                return;
            }
            const data = await response.json();
            if (data.success) {
                const newCount = data.count;
                const currentCount = this.getCurrentCount();
                this.updateFavoritesDisplay(newCount);

                if (newCount > currentCount) {
                    this.showUpdateAnimation(true);
                } else if (newCount < currentCount) {
                    this.showUpdateAnimation(false);
                }
            }
        } catch (error) {
            if (error.name === 'AuthenticationError') {
                this.handleLogout();
            }
        }
    }

    handleLogout() {
        this.updateFavoritesDisplay(0);
    }

    updateFavoritesDisplay(count) {
        const container = document.querySelector(this.selectors.container);
        if (!container) return;

        const heart = container.querySelector(this.selectors.heart);
        let bubble = container.querySelector(this.selectors.bubble);

        if (count > 0) {
            if (heart) {
                heart.className = 'fas fa-heart favorites-heart-filled fs-4';
            }

            if (!bubble) {
                bubble = this.createBubble();
                container.appendChild(bubble);
            }

            bubble.textContent = count;
            bubble.style.display = 'flex';

            if (count >= 10) {
                bubble.setAttribute('data-count', count.toString());
            } else {
                bubble.removeAttribute('data-count');
            }

        } else {
            if (heart) {
                heart.className = 'far fa-heart favorites-heart-empty fs-4';
            }

            if (bubble) {
                bubble.style.display = 'none';
            }
        }

        this.updateTitle(count);
    }

    createBubble() {
        const bubble = document.createElement('span');
        bubble.className = 'favorites-count-bubble';
        return bubble;
    }

    getCurrentCount() {
        const bubble = document.querySelector(this.selectors.bubble);
        if (!bubble || bubble.style.display === 'none') return 0;
        return parseInt(bubble.textContent, 10) || 0;
    }

    updateTitle(count) {
        const container = document.querySelector(this.selectors.container);
        if (container) {
            container.setAttribute('data-tooltip', `My favorites (${count})`);
        }
    }

    showUpdateAnimation(isAdded) {
        const container = document.querySelector(this.selectors.container);
        if (!container) return;

        container.style.animation = 'none';

        requestAnimationFrame(() => {
            if (isAdded) {
                container.style.animation = 'heartPulse 0.6s ease-out';
            } else {
                container.style.animation = 'heartShrink 0.4s ease-out';
            }

            setTimeout(() => {
                container.style.animation = '';
            }, 600);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new HeaderFavoritesHandler();
});
