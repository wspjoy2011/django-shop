import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';

class FavoriteBulkDelete extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'favorite-updates'});
        this.http = new AuthenticatedHttpClient();
        this.selectors = {
            meta: '#collection-meta',
            grid: '#collection-items-grid',
            checkbox: '.favorite-delete-checkbox',
            toolbar: '.admin-toolbar',
            button: '#bulk-delete-btn',
            selectAllBtn: '#select-all-btn',
            clearAllBtn: '#clear-all-btn'
        };

        this.init();

        this.updateToolbarVisibility();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('favorite_updated', () => {
            this.updateToolbarVisibility();
        });
    }

    bindEvents() {
        const grid = document.querySelector(this.selectors.grid);
        const button = document.querySelector(this.selectors.button);
        const selectAllBtn = document.querySelector(this.selectors.selectAllBtn);
        const clearAllBtn = document.querySelector(this.selectors.clearAllBtn);

        if (!grid || !button) return;

        grid.addEventListener('change', (e) => {
            if (e.target.matches(this.selectors.checkbox)) {
                this.updateToolbarVisibility();
            }
        });

        button.addEventListener('click', (e) => {
            e.preventDefault();
            void this.handleBulkDelete();
        });

        selectAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.selectAll();
        });

        clearAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.clearAll();
        });
    }

    selectAll() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return;
        const boxes = grid.querySelectorAll(this.selectors.checkbox);
        boxes.forEach((el) => {
            el.checked = true;
        });
        this.updateToolbarVisibility();
    }

    clearAll() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return;
        const boxes = grid.querySelectorAll(this.selectors.checkbox);
        boxes.forEach((el) => {
            el.checked = false;
        });
        this.updateToolbarVisibility();
    }

    getSelectedIds() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return [];
        return Array.from(grid.querySelectorAll(`${this.selectors.checkbox}:checked`))
            .map((input) => parseInt(input.value, 10));
    }

    updateToolbarVisibility() {
        const toolbar = document.querySelector(this.selectors.toolbar);
        const grid = document.querySelector(this.selectors.grid);
        if (!toolbar || !grid) return;

        const boxes = grid.querySelectorAll(this.selectors.checkbox);
        const selected = grid.querySelectorAll(`${this.selectors.checkbox}:checked`).length;

        toolbar.style.display = boxes.length > 0 ? '' : 'none';

        const deleteBtn = document.querySelector(this.selectors.button);
        if (deleteBtn) {
            deleteBtn.disabled = selected === 0;
        }
    }

    async handleBulkDelete() {
        const meta = document.querySelector(this.selectors.meta);
        const grid = document.querySelector(this.selectors.grid);
        const collectionId = meta.dataset.collectionId;

        const selected = this.getSelectedIds();
        if (!selected.length) {
            this.updateToolbarVisibility();
            return;
        }

        const url = `/api/v1/favorites/collections/${collectionId}/items/bulk-delete/`;
        const payload = {item_ids: selected};

        try {
            const resp = await this.http.sendJSON(url, payload, 'POST');
            await this.http.handleResponse(resp, grid, {
                onLoginRedirect: () => this.handleLogoutRedirect(meta),
                onSuccess: () => {
                    MessageManager.showGlobalMessage(
                        `Deleted ${selected.length} items successfully!`,
                        'success',
                        {timeout: 2000}
                    );
                    selected.forEach((id) => {
                        const node = grid.querySelector(`[data-item-id="${id}"]`);
                        if (node) node.remove();
                    });
                    this.updateToolbarVisibility();
                    this.broadcastManager.broadcast('favorite_updated', {});
                },
                onError: () => {
                    MessageManager.showGlobalMessage(
                        'Failed to delete items. Please try again.',
                        'error'
                    );
                }
            });
        } catch (_) {
            MessageManager.showGlobalMessage('Network error. Please try again.', 'error');
        }
    }

    handleLogoutRedirect(meta) {
        const slug = meta.dataset.collectionSlug;
        const username = meta.dataset.collectionUsername;
        const nextPath = `/favorites/collections/${username}/${slug}/`;
        const loginUrl = `/accounts/login/?next=${encodeURIComponent(nextPath)}`;

        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: loginUrl,
            message: 'Session expired. Please log in to delete items.'
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FavoriteBulkDelete();
});
