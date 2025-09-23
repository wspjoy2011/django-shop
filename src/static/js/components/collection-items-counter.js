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
            statsNumber: '.collection-stats .stat-number',
            templateScript: '#favorite-card-template',
            emptyState: '.collection-empty-state'
        };

        this.init();
        void this.updateCountAndUI();
    }

    bindEvents() {
        super.bindEvents();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('favorite_updated', () => {
            void this.updateCountAndUI();
        });
    }

    async updateCountAndUI() {
        const meta = document.querySelector(this.selectors.meta);
        const grid = document.querySelector(this.selectors.grid);
        const statsNumber = document.querySelector(this.selectors.statsNumber);

        const collectionId = meta.dataset.collectionId;
        const url = `/api/v1/favorites/collections/${collectionId}/count/`;

        try {
            const resp = await this.http.sendRequest(url, {
                method: 'GET',
                headers: {'Accept': 'application/json'}
            });

            return await this.http.handleResponse(resp, grid, {
                onLoginRedirect: () => this.handleLoginRedirect(meta),
                onSuccess: (data) => {
                    const count = Number.isFinite(data?.count) ? data.count : 0;
                    if (statsNumber) statsNumber.textContent = String(count);
                    this.toggleEmptyState(count === 0);
                },
                onError: () => {
                }
            });
        } catch (_) {
        }
    }

    toggleEmptyState(isEmpty) {
        const grid = document.querySelector(this.selectors.grid);

        let emptyEl = document.querySelector(this.selectors.emptyState);

        if (isEmpty) {
            if (!emptyEl) {
                const tpl = document.querySelector(this.selectors.templateScript);
                if (tpl && tpl.textContent) {
                    const wrapper = document.createElement('div');
                    wrapper.innerHTML = tpl.textContent;
                    const candidate = wrapper.querySelector(this.selectors.emptyState);
                    if (candidate) {
                        emptyEl = candidate;
                        emptyEl.style.display = '';
                        grid.parentNode.insertBefore(emptyEl, grid.nextSibling);
                    }
                }
            } else {
                emptyEl.style.display = '';
            }
            if (grid) grid.style.display = 'none';
        } else {
            if (emptyEl) emptyEl.style.display = 'none';
            if (grid) grid.style.display = '';
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
