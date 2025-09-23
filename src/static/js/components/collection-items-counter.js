import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';

class CollectionItemsCounter extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'favorite-updates'});
        this.http = new AuthenticatedHttpClient();

        this.selectors = {
            meta: '#collection-meta',
            grid: '#collection-items-grid',

            itemsCount: '#stat-items-count',
            totalValue: '#stat-total-value',
            currencySymbol: '#stat-currency-symbol',

            templateScript: '#favorite-card-template',
            emptyState: '.collection-empty-state'
        };

        this.init();
        void this.updateAll();
    }

    bindEvents() {
        super.bindEvents();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('favorite_updated', () => {
            void this.updateAll();
        });
    }

    async updateAll() {
        const meta = document.querySelector(this.selectors.meta);
        const grid = document.querySelector(this.selectors.grid);
        if (!meta || !grid) return;

        const collectionId = meta.dataset.collectionId;

        await this.fetchAndApplyJSON(
            `/api/v1/favorites/collections/${collectionId}/count/`,
            grid,
            (data) => {
                const count = Number.isFinite(data?.count) ? data.count : 0;
                const countEl = document.querySelector(this.selectors.itemsCount);
                if (countEl) countEl.textContent = String(count);
                this.toggleEmptyState(count === 0);
            },
            () => this.handleLoginRedirect(meta)
        );

        await this.fetchAndApplyJSON(
            `/api/v1/favorites/collections/${collectionId}/total-value/`,
            grid,
            (data) => {
                const valEl = document.querySelector(this.selectors.totalValue);
                const symEl = document.querySelector(this.selectors.currencySymbol);
                if (valEl) valEl.textContent = (data?.total_value ?? 0);
                if (symEl) symEl.textContent = (data?.currency_symbol ?? '');
            },
            () => this.handleLoginRedirect(meta)
        );
    }

    async fetchAndApplyJSON(url, contextNode, onSuccess, onLoginRedirect) {
        try {
            const resp = await this.http.sendRequest(url, {
                method: 'GET',
                headers: {'Accept': 'application/json'}
            });

            return await this.http.handleResponse(resp, contextNode, {
                onLoginRedirect,
                onSuccess: (data) => {
                    if (typeof onSuccess === 'function') onSuccess(data);
                },
                onError: () => {
                }
            });
        } catch (_) {
        }
    }

    toggleEmptyState(isEmpty) {
        const gridElement = document.querySelector(this.selectors.grid);
        const emptyStateElement = document.querySelector(this.selectors.emptyState);

        if (!gridElement || !emptyStateElement) return;

        if (isEmpty) {
            emptyStateElement.style.display = '';
            gridElement.style.display = 'none';
        } else {
            emptyStateElement.style.display = 'none';
            gridElement.style.display = '';
        }
    }

    handleLoginRedirect(meta) {
        const slug = meta.dataset.collectionSlug;
        const username = meta.dataset.collectionUsername;
        const nextPath = `/favorites/collections/${username}/${slug}/`;
        const loginUrl = `/accounts/login/?next=${encodeURIComponent(nextPath)}`;

        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: loginUrl,
            message: 'Session expired. Please log in.'
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionItemsCounter();
});
