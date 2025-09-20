import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';

class FavoritePrivacyToggle extends BaseComponent {
    constructor() {
        super({});
        this.selectors = {
            meta: '#collection-meta',
            badge: '#collection-visibility-badge',
        };
        this.http = new AuthenticatedHttpClient();
        this.bindEvents();
    }

    bindEvents() {
        const meta = document.querySelector(this.selectors.meta);
        if (!meta) return;

        const isOwner = meta.dataset.isOwner === '1';
        const badge = document.querySelector(this.selectors.badge);
        if (!badge) return;

        if (isOwner) {
            badge.style.cursor = 'pointer';
            badge.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleVisibility(meta, badge);
            });
        }
    }

    showSpinner(badge) {
        if (!badge.dataset.origHtml) {
            badge.dataset.origHtml = badge.innerHTML;
        }
        badge.classList.add('is-loading');
        badge.innerHTML = `<span class="toggle-spinner" aria-hidden="true"></span>Updating…`;
    }

    hideSpinner(badge) {
        badge.classList.remove('is-loading');
    }

    async toggleVisibility(meta, badge) {
        const url = meta.dataset.toggleUrl;

        this.showSpinner(badge);
        try {
            const resp = await this.http.sendRequest(url, {
                method: 'POST',
                headers: {'Accept': 'application/json'},
                body: JSON.stringify({}),
            });

            await this.http.handleResponse(resp, meta, {
                onLoginRedirect: () => {
                    this.hideSpinner(badge);
                    this.redirectToLogin(meta);
                },
                onSuccess: (data) => {
                    this.applyBadgeState(badge, data?.is_public === true);
                    this.hideSpinner(badge);
                },
                onError: () => {
                    this.hideSpinner(badge);
                    if (badge.dataset.origHtml) badge.innerHTML = badge.dataset.origHtml;
                    MessageManager.showGlobalMessage('Failed to toggle visibility.', 'error');
                },
            });
        } catch (_) {
            this.hideSpinner(badge);
            if (badge.dataset.origHtml) badge.innerHTML = badge.dataset.origHtml;
            MessageManager.showGlobalMessage('Network error. Please try again.', 'error');
        }
    }

    redirectToLogin(meta) {
        const slug = meta.dataset.collectionSlug;
        const username = meta.dataset.collectionUsername;
        const nextPath = `/favorites/collections/${username}/${slug}/`;
        const loginUrl = `/accounts/login/?next=${encodeURIComponent(nextPath)}`;

        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: loginUrl,
            redirectTimeout: 1800,
        });
    }

    applyBadgeState(badge, isPublic) {
        if (isPublic) {
            badge.classList.remove('badge-soft');
            badge.classList.add('badge-soft-success');
            badge.innerHTML = '<i class="fas fa-lock-open me-1"></i>Public';
            MessageManager.showGlobalMessage(
                'Collection is now Public.',
                'success',
                {timeout: 1800}
            );
        } else {
            badge.classList.remove('badge-soft-success');
            badge.classList.add('badge-soft');
            badge.innerHTML = '<i class="fas fa-lock me-1"></i>Private';
            MessageManager.showGlobalMessage(
                'Collection is now Private.',
                'success',
                {timeout: 1800}
            );
        }
        badge.dataset.origHtml = badge.innerHTML;
    }

}

document.addEventListener('DOMContentLoaded', () => {
    new FavoritePrivacyToggle();
});
