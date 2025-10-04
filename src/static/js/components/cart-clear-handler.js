import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class CartClearHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'cart-updates'});

        this.selectors = {
            clearButton: '#cart-clear-btn',
            modal: '#cart-clear-modal',
            modalClose: '#cart-clear-modal .modal-close',
            modalCancel: '#cart-clear-modal .modal-cancel',
            modalConfirm: '#cart-clear-modal .modal-confirm',
            confirmSpinner: '#cart-clear-modal .loading-spinner',
            confirmText: '#cart-clear-modal .btn-text',
            layout: '#cart-layout',
            itemsContainer: '.cart-items',
            itemCard: '.cart-item-card',
            emptyTemplate: '#cart-empty-template',
            summaryCol: '#cart-summary-col'
        };

        this.http = new AuthenticatedHttpClient();

        this.events = {
            cartCleared: 'cart_cleared',
            qtyChanged: 'cart_item_quantity_changed'
        };

        this.init();
    }

    bootstrapInitialState() {
        const button = document.querySelector(this.selectors.clearButton);
        if (!button) return
        button.addEventListener('click', () => this.openModal());
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe(this.events.cartCleared, () => {
            this.applyClearedUi();
        });
    }

    bindEvents() {
        const modal = document.querySelector(this.selectors.modal);
        if (!modal) return

        const closeBtn = document.querySelector(this.selectors.modalClose);
        const cancelBtn = document.querySelector(this.selectors.modalCancel);
        const confirmBtn = document.querySelector(this.selectors.modalConfirm);

        closeBtn.addEventListener('click', () => this.closeModal());
        cancelBtn.addEventListener('click', () => this.closeModal());
        confirmBtn.addEventListener('click', () => this.onConfirmClear());
        modal.querySelector('.modal-overlay')
            .addEventListener('click', () => this.closeModal());
    }

    openModal() {
        const modal = document.querySelector(this.selectors.modal);
        modal.classList.remove('hidden');
    }

    closeModal() {
        const modal = document.querySelector(this.selectors.modal);
        modal.classList.add('hidden');
    }

    setConfirmLoading(isLoading) {
        const btn = document.querySelector(this.selectors.modalConfirm);
        const spinner = document.querySelector(this.selectors.confirmSpinner);
        const text = document.querySelector(this.selectors.confirmText);

        btn.disabled = isLoading;
        spinner.classList.toggle('hidden', !isLoading);
        text.classList.toggle('hidden', isLoading);
    }

    async onConfirmClear() {
        const button = document.querySelector(this.selectors.clearButton);
        const url = button.dataset.clearUrl;

        this.setConfirmLoading(true);
        const resp = await this.http.sendRequest(url, {method: 'DELETE'});
        this.setConfirmLoading(false);

        if (resp.status !== 204) return

        this.closeModal();
        this.applyClearedUi();
        this.broadcastManager.broadcast(this.events.cartCleared, {});
        this.broadcastManager.broadcast(this.events.qtyChanged, {});
    }

    applyClearedUi() {
        const summaryCol = document.querySelector(this.selectors.summaryCol);
        if (summaryCol) summaryCol.remove();

        const layout = document.querySelector(this.selectors.layout);
        const tpl = document.querySelector(this.selectors.emptyTemplate);

        if (layout && tpl) {
            layout.insertAdjacentHTML('beforebegin', tpl.innerHTML);
            layout.remove();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CartClearHandler();
});
