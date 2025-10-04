import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class CartSummaryHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});

        this.selectors = {
            container: '#cart-summary',
            items: '#cart-summary-items',
            quantity: '#cart-summary-quantity',
            subtotal: '#cart-summary-subtotal',
            discount: '#cart-summary-discount',
            total: '#cart-summary-total'
        };

        this.http = new AuthenticatedHttpClient();

        this.init();
    }

    bootstrapInitialState() {
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('cart_item_quantity_changed', () => {
            void this.fetchAndRender();
        });

        this.broadcastManager.subscribe('cart_item_removed', () => {
            void this.fetchAndRender();
        });
    }

    async fetchAndRender() {
        const container = document.querySelector(this.selectors.container);
        if (!container) return

        const url = container.dataset.summaryUrl;
        const resp = await this.http.sendRequest(url, {method: 'GET'});
        if (!resp.ok) return

        const data = await resp.json();
        this.updateDisplay(data);
    }

    updateDisplay(data) {
        const itemsElement = document.querySelector(this.selectors.items);
        const quantityElement = document.querySelector(this.selectors.quantity);
        const subtotalElement = document.querySelector(this.selectors.subtotal);
        const discountElement = document.querySelector(this.selectors.discount);
        const totalElement = document.querySelector(this.selectors.total);

        itemsElement.textContent = String(data.total_items);
        quantityElement.textContent = String(data.total_quantity);
        subtotalElement.textContent = String(data.total_subtotal);
        discountElement.textContent = String(data.total_discount);
        totalElement.textContent = String(data.total_value);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CartSummaryHandler();
});
