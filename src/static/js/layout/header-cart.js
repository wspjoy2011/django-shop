import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class HeaderCartHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});

        this.selectors = {
            container: '.cart-icon-container',
            icon: '.cart-filled, .cart-empty',
            bubble: '.cart-count-bubble',
        };

        this.summaryUrl = '/api/v1/cart/summary/';
        this.http = new AuthenticatedHttpClient();

        this.init();
    }

    bootstrapInitialState() {
        const container = document.querySelector(this.selectors.container);
        if (container) void this.fetchAndUpdateSummary();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('cart_updated', () => {
            void this.fetchAndUpdateSummary();
        });
    }

    async fetchAndUpdateSummary() {
        const container = document.querySelector(this.selectors.container);
        if (!container) return;

        try {
            const resp = await this.http.sendRequest(this.summaryUrl, {method: 'GET'});
            if (!resp.ok) return;

            const payload = await resp.json();

            const data = payload.success ? payload : payload;
            const itemsCount = Number(data.items_count) || 0;
            const totalQty = Number(data.total_quantity) || 0;
            const totalVal = data.total_value ?? '0.00';

            this.updateDisplay(itemsCount, totalQty, totalVal);
        } catch (_) {
        }
    }

    updateDisplay(itemsCount, totalQty, totalVal) {
        const container = document.querySelector(this.selectors.container);
        if (!container) return;

        let icon = container.querySelector(this.selectors.icon);
        if (!icon) {
            icon = document.createElement('i');
            icon.className = 'fas fa-shopping-cart cart-empty fs-4';
            container.appendChild(icon);
        }
        icon.className = itemsCount > 0
            ? 'fas fa-shopping-cart cart-filled fs-4'
            : 'fas fa-shopping-cart cart-empty fs-4';

        let bubble = container.querySelector(this.selectors.bubble);
        if (itemsCount > 0) {
            if (!bubble) {
                bubble = document.createElement('span');
                bubble.className = 'cart-count-bubble';
                container.appendChild(bubble);
            }
            bubble.textContent = String(itemsCount);
            bubble.style.display = 'flex';

            if (itemsCount >= 10) bubble.setAttribute('data-count', String(itemsCount));
            else bubble.removeAttribute('data-count');
        } else if (bubble) {
            bubble.style.display = 'none';
            bubble.removeAttribute('data-count');
        }

        container.setAttribute(
            'data-tooltip',
            `Cart • Items: ${itemsCount} • Qty: ${totalQty} • Total: ${totalVal}`
        );
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new HeaderCartHandler();
});
