import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {LoadingStateManager} from '../utils/components/LoadingStateManager.js';
import {MessageManager} from '../utils/components/MessageManager.js';

class CartButtonHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});

        this.selectors = {
            component: '.cart-component',
            button: '.cart-btn',
            count: '.cart-count',
            messages: '.cart-messages-container',
            container: '.cart-container',
            iconCheck: '.cart-check',
            iconCart: '.cart-icon',
        };

        this.cssClasses = {
            active: 'cart-active',
            disabled: 'disabled',
        };

        this.http = new AuthenticatedHttpClient();
        this.init();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('cart_updated', (data) => {
            const {productId, inCart, cartCount} = data || {};
            if (!productId) return;
            const components = document.querySelectorAll(
                `${this.selectors.component}[data-product-id="${productId}"]`
            );
            components.forEach((c) => this.updateCartState(c, inCart, cartCount));
        });
    }

    bindEvents() {
        super.bindEvents();

        document.addEventListener('click', (e) => {
            const button = e.target.closest(this.selectors.button);
            if (!button) return;

            const component = button.closest(this.selectors.component);
            if (!component) return;

            e.preventDefault();
            void this.onCartClick(component);
        });
    }

    bootstrapInitialState() {
        document.querySelectorAll(this.selectors.component).forEach((comp) => {
            const inCart = comp.dataset.inCart === 'true';
            this.updateCartState(comp, inCart);
        });
    }

    async onCartClick(component) {
        if (LoadingStateManager.isLoading(component, {
            selector: this.selectors.button,
            cssClass: this.cssClasses.disabled
        })) {
            return;
        }

        const productId = component.dataset.productId;
        if (!productId) return;

        const url = component.dataset.cartUrl;

        try {
            this.setLoadingState(component, true);

            const resp = await this.http.sendRequest(url, {
                method: 'POST',
                headers: {'Accept': 'application/json'}
            });

            await this.http.handleResponse(resp, component, {
                onSuccess: (data) => this.handleSuccess(component, data),
                onError: () => this.handleError(component)
            });

        } catch (err) {
            this.handleError(component);
        } finally {
            this.setLoadingState(component, false);
        }
    }

    handleSuccess(component, data) {
        const inCart = !!data?.in_cart;
        const cartCount = Number.isFinite(data?.cart_count) ? data.cart_count : null;

        const productId = component.dataset.productId;
        const components = document.querySelectorAll(
            `${this.selectors.component}[data-product-id="${productId}"]`
        );
        components.forEach((c) => this.updateCartState(c, inCart, cartCount));

        this.broadcastManager.broadcast('cart_updated', {
            productId,
            inCart,
            cartCount
        });
    }

    handleError(component) {
        MessageManager.showGlobalMessage('Failed to update cart. Please try again.', 'error',
            component.querySelector(this.selectors.messages));
    }

    _className(selector) {
        return selector.startsWith('.') ? selector.slice(1) : selector;
    }

    applyIconState(component, inCart) {
        const iconEl =
            component.querySelector(this.selectors.iconCheck) ||
            component.querySelector(this.selectors.iconCart);

        if (!iconEl) return;

        const checkCls = this._className(this.selectors.iconCheck);
        const cartCls = this._className(this.selectors.iconCart);

        iconEl.classList.remove(checkCls, cartCls, 'fa-check', 'fa-shopping-cart');

        if (inCart) {
            iconEl.classList.add('fas', 'fa-check', checkCls);
        } else {
            iconEl.classList.add('fas', 'fa-shopping-cart', cartCls);
        }
    }

    updateCartState(component, inCart, count = null) {
        component.dataset.inCart = inCart ? 'true' : 'false';
        component.classList.toggle(this.cssClasses.active, inCart);

        this.applyIconState(component, inCart);

        const checkIcon = component.querySelector(this.selectors.iconCheck);
        const cartIcon = component.querySelector(this.selectors.iconCart);
        if (checkIcon) checkIcon.style.display = inCart ? '' : 'none';
        if (cartIcon) cartIcon.style.display = inCart ? 'none' : '';

        const title = inCart ? 'Remove from cart' : 'Add to cart';
        const btn = component.querySelector(this.selectors.button);
        const container = component.querySelector(this.selectors.container);
        if (btn) btn.setAttribute('title', title);
        if (container) container.setAttribute('title', title);

        if (count !== null) {
            const el = component.querySelector(this.selectors.count);
            if (el) el.textContent = String(count);
        }
    }

    setLoadingState(component, isLoading) {
        LoadingStateManager.setLoadingState(component, isLoading, {
            selectors: {button: this.selectors.button},
            cssClasses: {disabled: this.cssClasses.disabled}
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CartButtonHandler();
});
