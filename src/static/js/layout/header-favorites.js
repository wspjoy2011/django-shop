class HeaderFavoritesHandler {
    constructor() {
        this.selectors = {
            container: '.favorites-heart-container',
            heart: '.favorites-heart-filled, .favorites-heart-empty',
            bubble: '.favorites-count-bubble'
        };

        this.init();
    }

    init() {
        this.setupBroadcastChannel();
        this.initializeState();
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
                this.handleFavoriteUpdate(data);
                break;
            case 'logout_detected':
                this.handleLogout();
                break;
        }
    }

    handleFavoriteUpdate(data) {
        const {action, favoritesCount} = data;

        const currentCount = this.getCurrentCount();
        let newCount;

        if (action === 'added') {
            newCount = currentCount + 1;
        } else if (action === 'removed') {
            newCount = Math.max(0, currentCount - 1);
        } else {
            newCount = favoritesCount || 0;
        }

        this.updateFavoritesDisplay(newCount);
        this.showUpdateAnimation(action === 'added');
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
        return parseInt(bubble.textContent) || 0;
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

    initializeState() {
        const bubble = document.querySelector(this.selectors.bubble);
        if (bubble) {
            const count = parseInt(bubble.textContent) || 0;
            this.updateTitle(count);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new HeaderFavoritesHandler();
});
