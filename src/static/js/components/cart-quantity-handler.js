import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class CartQuantityHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});
        this.selectors = {
            component: '.cart-items',
            itemCard: '.cart-item-card',
            buttonIncrease: '[data-increase-url]',
            buttonDecrease: '[data-decrease-url]',
            quantityValueById: (id) => `#cart-item-qty-${id}`,
            totalValueById: (id) => `#cart-item-total-${id}`,
            stepperContainer: '.qty-stepper',
            spinner: '.qty-spinner',
            messages: '.cart-messages-container'
        };
        this.cssClasses = { disabled: 'is-disabled', hidden: 'is-hidden' };
        this.httpClient = new AuthenticatedHttpClient();
        this.maxQuantityByItemId = new Map();
        this.init();
    }

    bindEvents() {
        super.bindEvents();
        document.addEventListener('click', (event) => {
            const incBtn = event.target.closest(this.selectors.buttonIncrease);
            if (incBtn) {
                const card = incBtn.closest(this.selectors.itemCard);
                event.preventDefault();
                void this.onChange(card, incBtn.dataset.increaseUrl);
                return;
            }
            const decBtn = event.target.closest(this.selectors.buttonDecrease);
            if (decBtn) {
                const card = decBtn.closest(this.selectors.itemCard);
                event.preventDefault();
                void this.onChange(card, decBtn.dataset.decreaseUrl);
            }
        });
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('cart_item_updated', (payload) => {
            this.updateUiFromPayload(payload);
        });
        this.broadcastManager.subscribe('cart_item_removed', (payload) => {
            this.updateUiRemoved(payload);
        });
    }

    setLoadingState(stepperContainer, isLoading) {
        const card = stepperContainer.closest(this.selectors.itemCard);
        this.toggleButtons(card, {
            disableIncrease: isLoading,
            disableDecrease: isLoading
        });
        this.toggleSpinner(stepperContainer, isLoading);
    }

    toggleSpinner(stepperContainer, isOn) {
        const spinnerEl = stepperContainer.querySelector(this.selectors.spinner);
        if (spinnerEl) spinnerEl.classList.toggle(this.cssClasses.hidden, !isOn);
    }

    async onChange(itemCardElement, requestUrl) {
        const stepper = itemCardElement.querySelector(this.selectors.stepperContainer);

        this.setLoadingState(stepper, true);

        const outcome = { ok: false, errorKey: null, quantity: null, payload: null };

        try {
            await this.httpClient.handleResponse(
                await this.httpClient.sendRequest(requestUrl, { method: 'POST' }),
                itemCardElement,
                {
                    onSuccess: (data) => {
                        outcome.ok = true;
                        outcome.payload = data;
                        outcome.quantity = typeof data?.quantity === 'number' ? data.quantity : null;
                    },
                    onError: (err) => {
                        outcome.ok = false;
                        outcome.errorKey = err?.error_key || null;
                        outcome.message = err?.message || 'Operation failed';
                    }
                }
            );
        } finally {
            this.toggleSpinner(stepper, false);

            if (outcome.ok && outcome.payload) {
                this.updateUiFromPayload(outcome.payload);
                this.broadcastManager.broadcast('cart_item_updated', outcome.payload);
            } else {
                this.onErrorFinal(itemCardElement, outcome);
            }
        }
    }

    onErrorFinal(itemCardElement, outcome) {
        const errorKey = outcome.errorKey || '';
        const isAvailability = errorKey === 'not_enough_stock' || errorKey === 'product_unavailable';
        const message = outcome.message || 'Operation failed';

        MessageManager.showGlobalMessage(message, isAvailability ? 'warning' : 'error');

        if (errorKey === 'not_enough_stock') {
            const itemId = this.getItemIdFromCard(itemCardElement);
            const currentQuantity = this.getCurrentQuantity(itemCardElement);
            if (itemId != null && currentQuantity != null) {
                this.maxQuantityByItemId.set(itemId, currentQuantity);
                this.adjustButtonsForQuantity(itemCardElement, currentQuantity);
            } else {
                this.toggleButtons(
                    itemCardElement,
                    { disableIncrease: true, disableDecrease: false }
                );
            }
            return;
        }

        if (errorKey === 'product_unavailable') {
            this.toggleButtons(
                itemCardElement,
                { disableIncrease: true, disableDecrease: false }
            );
            return;
        }

        this.toggleButtons(
            itemCardElement,
            { disableIncrease: false, disableDecrease: false }
        );
    }

    updateUiFromPayload(payload) {
        const qtyEl = document.querySelector(this.selectors.quantityValueById(payload.id));
        if (qtyEl) qtyEl.textContent = String(payload.quantity);

        const totalEl = document.querySelector(this.selectors.totalValueById(payload.id));
        if (totalEl && payload.price && payload.price.current_price) {
            totalEl.textContent =
                `${payload.price.current_price} × ${payload.quantity} = ${payload.price.total_price}`;
        }

        const card = qtyEl ? qtyEl.closest(this.selectors.itemCard) : null;
        if (card) this.adjustButtonsForQuantity(card, payload.quantity);
    }

    updateUiRemoved(payload) {
        const qtyEl = document.querySelector(this.selectors.quantityValueById(payload.id));
        if (!qtyEl) return;
        qtyEl.textContent = '0';

        const card = qtyEl.closest(this.selectors.itemCard);
        if (card) {
            const itemId = this.getItemIdFromCard(card);
            if (itemId != null) this.maxQuantityByItemId.delete(itemId);
            this.toggleButtons(card, { disableIncrease: false, disableDecrease: true });
        }
    }

    getItemIdFromCard(card) {
        const qtyEl = card.querySelector('.qty-value');
        if (!qtyEl) return null;
        const idAttr = qtyEl.id || '';
        const parts = idAttr.split('cart-item-qty-');
        return parts.length === 2 ? Number(parts[1]) : null;
    }

    getCurrentQuantity(card) {
        const qtyEl = card.querySelector('.qty-value');
        if (!qtyEl) return null;
        const val = parseInt(qtyEl.textContent, 10);
        return Number.isNaN(val) ? null : val;
    }

    adjustButtonsForQuantity(card, quantity) {
        const itemId = this.getItemIdFromCard(card);
        const max = this.maxQuantityByItemId.get(itemId);
        const disableDecrease = quantity <= 1;
        const disableIncrease = typeof max === 'number' ? quantity >= max : false;

        this.toggleButtons(card, { disableIncrease, disableDecrease });
    }

    toggleButtons(card, { disableIncrease, disableDecrease }) {
        const incBtn = card.querySelector(this.selectors.buttonIncrease);
        const decBtn = card.querySelector(this.selectors.buttonDecrease);
        if (incBtn) incBtn.toggleAttribute('disabled', !!disableIncrease);
        if (decBtn) decBtn.toggleAttribute('disabled', !!disableDecrease);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CartQuantityHandler();
});
