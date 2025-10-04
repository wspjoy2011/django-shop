import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class CartItemRemoveHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});

        this.selectors = {
            container: '.cart-items',
            itemCard: '.cart-item-card',
            removeButton: '[data-remove-url]',
            emptyTemplate: '#cart-empty-template',
            layout: '#cart-layout',
            clearButton: '.cart-clear-btn'
        };

        this.http = new AuthenticatedHttpClient();

        this.events = {
            itemRemoved: 'cart_item_removed'
        };

        this.init();
    }

    bootstrapInitialState() {
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe(this.events.itemRemoved, (payload) => {
            this.removeCardByItemId(payload.item_id);
        });
    }

    bindEvents() {
        const container = document.querySelector(this.selectors.container);
        if (!container) return
        container.addEventListener('click', (e) => {
            const button = e.target.closest(this.selectors.removeButton);
            if (!button) return
            void this.onRemoveClick(button);
        });
    }

    async onRemoveClick(button) {
        const url = button.dataset.removeUrl;
        const card = button.closest(this.selectors.itemCard);
        const itemId = this.getItemIdFromCard(card);

        const resp = await this.http.sendRequest(url, {method: 'DELETE'});
        if (resp.status !== 204) return

        this.removeCard(card);
        this.broadcastManager.broadcast(this.events.itemRemoved, {item_id: itemId});
    }

    getItemIdFromCard(card) {
        const id = card.id.replace('cart-item-card-', '');
        return Number(id);
    }

    removeCard(card) {
        card.remove();
        this.onListChanged();
    }

    removeCardByItemId(itemId) {
        const card = document.getElementById(`cart-item-card-${itemId}`);
        if (!card) return
        this.removeCard(card);
    }

    onListChanged() {
        const container = document.querySelector(this.selectors.container);
        if (!container) return

        const hasItems = container.querySelector(this.selectors.itemCard) != null;
        if (hasItems) return

        const layout = document.querySelector(this.selectors.layout);
        const template = document.querySelector(this.selectors.emptyTemplate);
        const clearButton = document.querySelector(this.selectors.clearButton);

        if (clearButton) clearButton.remove();
        if (layout && template) {
            layout.insertAdjacentHTML('beforebegin', template.innerHTML);
            layout.remove();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CartItemRemoveHandler();
});
