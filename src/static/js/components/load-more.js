import {BaseComponent} from '../utils/components/BaseComponent.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {LoadingStateManager} from '../utils/components/LoadingStateManager.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';

class LoadMoreFavorites extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'favorite-items'});
        this.selectors = {
            grid: '#collection-items-grid',
            container: '.load-more-container',
            button: '#load-more-btn',
            spinner: '.spinner-border',

            cardItem: '.draggable-item',
            card: '.favorite-card',
            imageLink: '.favorite-image-link',
            image: '.favorite-image',
            titleLink: '.favorite-title a',
            titleDisabled: '.favorite-title .disabled-title',

            statusAvailable: '.status-badge.available',
            statusOutOfStock: '.status-badge.out-of-stock',
            statusUnavailable: '.status-badge.unavailable',

            priceWrapper: '.favorite-price-section .price-wrapper',
            priceRegular: '.price-regular',
            priceRegularValue: '.price-regular .current-price .price-value',
            priceOnSale: '.price-on-sale',
            saleValue: '.price-on-sale .sale-price .price-value',
            originalValue: '.price-on-sale .original-price .price-value',
            discountValue: '.price-on-sale .discount-badge .discount-value',
            priceUnavailable: '.price-unavailable',

            noteBlock: '.favorite-note',
            noteText: '.favorite-note .note-text',
            templateScript: '#favorite-card-template',

            pagination: {
                nav: 'nav[aria-label="Page navigation"]',
                first: '#pg-first',
                prev: '#pg-prev',
                next: '#pg-next',
                last: '#pg-last',
                current: '#pg-current'
            }
        };

        this.cssClasses = {
            disabled: 'disabled',
            unavailable: 'unavailable'
        };

        this.baseUrl = '/api/v1/favorites/collections';
        this.http = new AuthenticatedHttpClient();
        this.templateHTML = this.getTemplateHTML();

        this.init();
    }

    getTemplateHTML() {
        const s = document.querySelector(this.selectors.templateScript);
        return s && s.textContent ? s.textContent.trim() : '';
    }

    bindEvents() {
        super.bindEvents();
        document.addEventListener('click', (e) => {
            const button = e.target.closest(this.selectors.button);
            if (!button) return;
            const container = button.closest(this.selectors.container);
            const grid = document.querySelector(this.selectors.grid);
            if (!container || !grid) return;
            e.preventDefault();
            void this.onLoadMore(container, grid);
        });
    }

    bootstrapInitialState() {
        document.querySelectorAll(this.selectors.container).forEach((c) => {
            if (!c.dataset.nextPage || c.dataset.nextPage === 'null') c.style.display = 'none';
        });
    }

    setLoadingState(container, isLoading) {
        LoadingStateManager.setLoadingState(container, isLoading, {
            selectors: {button: this.selectors.button, loadingSpinner: this.selectors.spinner},
            cssClasses: {disabled: this.cssClasses.disabled},
            disablePointerEvents: true
        });
    }

    handleLogoutDetection(container) {
        const slug = container?.dataset.collectionSlug;
        const username = container?.dataset.collectionUsername;
        const nextPath = `/favorites/collections/${username}/${slug}/`;
        const loginUrl = `/accounts/login/?next=${encodeURIComponent(nextPath)}`;

        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: loginUrl,
            redirectTimeout: 2000
        });
    }

    async onLoadMore(container, grid) {
        const collectionId = container.dataset.collectionId;
        const nextPage = container.dataset.nextPage;
        if (!collectionId || !nextPage) {
            container.style.display = 'none';
            return;
        }

        const loadedPage = parseInt(nextPage, 10);

        this.setLoadingState(container, true);
        try {
            const url = `${this.baseUrl}/${collectionId}/items/?page=${encodeURIComponent(nextPage)}`;
            const resp = await this.http.sendRequest(url, {
                method: 'GET',
                headers: {'Accept': 'application/json'}
            });

            if (resp.status === 404) {
                this.handleLogoutDetection(container);
                return;
            }

            await this.http.handleResponse(resp, container, {
                onLoginRedirect: () => this.handleLogoutDetection(container),
                onSuccess: (data) => this.handleSuccessPage(data, grid, container, loadedPage),
                onError: () => {
                    MessageManager.showGlobalMessage(
                        'Failed to load more items. Please try again.',
                        'error'
                    );
                }
            });
        } catch (err) {
            MessageManager.showGlobalMessage('Network error. Please try again.', 'error');
        } finally {
            this.setLoadingState(container, false);
        }
    }

    handleSuccessPage(data, grid, container, loadedPage) {
        if (!data || !Array.isArray(data.results)) {
            MessageManager.showGlobalMessage('Unexpected server response.', 'error');
            return;
        }

        const fragment = document.createDocumentFragment();
        for (const favoriteItem of data.results) {
            const node = this.buildNodeFromTemplate(favoriteItem, container);
            if (node) fragment.appendChild(node);
        }
        if (fragment.children.length) {
            grid.appendChild(fragment);
        }

        const currentPage = Number.isFinite(loadedPage) ? loadedPage : null;
        const hasNext = Boolean(data.next);

        this.updatePaginationUI(currentPage, hasNext);

        if (!hasNext) {
            container.style.display = 'none';
            return;
        }

        const nextPage = new URL(data.next, window.location.origin)
            .searchParams.get('page');

        if (nextPage) {
            container.dataset.nextPage = String(nextPage);
        } else {
            container.style.display = 'none';
        }
    }

    buildNodeFromTemplate(favoriteItem, container) {
        if (!this.templateHTML) return null;
        const wrapper = document.createElement('div');
        wrapper.innerHTML = this.templateHTML;
        const node = wrapper.firstElementChild;
        if (!node) return null;

        const product = favoriteItem.product || {};
        const inventory = product.inventory || {};
        const isOwner = container?.dataset.isOwner === '1';
        const isActive = !!inventory.is_active;
        const isInStock = !!inventory.is_in_stock;
        const isAvailable = isActive && isInStock;

        node.setAttribute('data-item-id', String(favoriteItem.id));
        node.setAttribute('data-position', String(favoriteItem.position));

        this.toggleDragHandle(node, isOwner);
        this.updateCard(node, isAvailable);
        this.updateImage(node, product, isAvailable);
        this.updateTitle(node, product, isAvailable);
        this.updateStatus(node, isAvailable, isActive);
        this.updatePrice(node, inventory, isAvailable);
        this.updateNote(node, favoriteItem.note);

        return node;
    }

    toggleDragHandle(node, isOwner) {
        const dragHandle = node.querySelector('.drag-handle');
        if (dragHandle) dragHandle.style.display = isOwner ? '' : 'none';
    }

    updateCard(node, isAvailable) {
        const card = node.querySelector(this.selectors.card);
        if (card) card.classList.toggle(this.cssClasses.unavailable, !isAvailable);
    }

    updateImage(node, product, isAvailable) {
        const imageElement = node.querySelector(this.selectors.image);
        const imageLinkElement = node.querySelector(this.selectors.imageLink);
        const productUrl = product.slug ? `/catalog/${product.slug}/` : '#';

        if (imageElement) {
            if (product.image_url) {
                imageElement.src = product.image_url;
                imageElement.alt = product.product_display_name || 'Product';
            } else {
                imageElement.removeAttribute('src');
                imageElement.alt = 'No image';
            }
        }
        if (imageLinkElement) {
            if (isAvailable) {
                imageLinkElement.classList.remove('disabled');
                imageLinkElement.setAttribute('href', productUrl);
            } else {
                imageLinkElement.classList.add('disabled');
                imageLinkElement.removeAttribute('href');
            }
        }
    }

    updateTitle(node, product, isAvailable) {
        const titleLink = node.querySelector(this.selectors.titleLink);
        const titleDisabled = node.querySelector(this.selectors.titleDisabled);
        const titleText = product.product_display_name || 'Product';
        const productUrl = product.slug ? `/catalog/${product.slug}/` : '#';

        if (isAvailable) {
            if (titleDisabled) titleDisabled.style.display = 'none';
            if (titleLink) {
                titleLink.textContent = titleText;
                titleLink.setAttribute('href', productUrl);
            }
        } else {
            if (titleLink) titleLink.remove();
            if (titleDisabled) {
                titleDisabled.textContent = titleText;
                titleDisabled.style.display = '';
            }
        }
    }

    updateStatus(node, isAvailable, isActive) {
        const sbAvail = node.querySelector(this.selectors.statusAvailable);
        const sbOos = node.querySelector(this.selectors.statusOutOfStock);
        const sbUnav = node.querySelector(this.selectors.statusUnavailable);
        if (sbAvail && sbOos && sbUnav) {
            sbAvail.style.display = isAvailable ? '' : 'none';
            sbOos.style.display = (!isAvailable && isActive) ? '' : 'none';
            sbUnav.style.display = (!isAvailable && !isActive) ? '' : 'none';
        }
    }

    updatePrice(node, inventory, isAvailable) {
        const priceRegular = node.querySelector(this.selectors.priceRegular);
        const priceRegularValue = node.querySelector(this.selectors.priceRegularValue);
        const priceOnSale = node.querySelector(this.selectors.priceOnSale);
        const saleValue = node.querySelector(this.selectors.saleValue);
        const originalValue = node.querySelector(this.selectors.originalValue);
        const discountValue = node.querySelector(this.selectors.discountValue);
        const priceUnavailable = node.querySelector(this.selectors.priceUnavailable);

        if (!isAvailable) {
            if (priceRegular) priceRegular.style.display = 'none';
            if (priceOnSale) priceOnSale.style.display = 'none';
            if (priceUnavailable) priceUnavailable.style.display = '';
            return;
        }

        const symbol = inventory.currency?.symbol || '$';
        const base = inventory.base_price;
        const sale = inventory.sale_price;
        const onSale = !!inventory.is_on_sale;
        const current = inventory.current_price != null ? inventory.current_price : base;

        if (priceUnavailable) priceUnavailable.style.display = 'none';

        if (onSale && sale != null) {
            if (priceRegular) priceRegular.style.display = 'none';
            if (priceOnSale) {
                priceOnSale.style.display = '';
                if (saleValue) saleValue.textContent = `${symbol}${sale}`;
                if (originalValue) originalValue.textContent = `${symbol}${base}`;
                if (discountValue) discountValue.textContent = `${inventory.discount_percentage || 0}%`;
            }
        } else {
            if (priceOnSale) priceOnSale.style.display = 'none';
            if (priceRegular) {
                priceRegular.style.display = '';
                if (priceRegularValue) priceRegularValue.textContent = `${symbol}${current}`;
            }
        }
    }

    updateNote(node, note) {
        const noteBlock = node.querySelector(this.selectors.noteBlock);
        const noteText = node.querySelector(this.selectors.noteText);
        if (note) {
            if (noteText) noteText.textContent = note;
            if (noteBlock) noteBlock.style.display = '';
        } else {
            if (noteBlock) noteBlock.style.display = 'none';
        }
    }

    updatePaginationUI(currentPage, hasNext) {
        const nav = document.querySelector(this.selectors.pagination.nav);
        if (!nav) return;

        const params = new URLSearchParams(window.location.search);
        const startPage = parseInt(params.get('page') || '1', 10);

        nav.querySelectorAll('li.page-item').forEach((li) => {
            const el = li.querySelector('.page-link');
            if (!el) return;

            const text = (el.textContent || '').trim();
            if (!/^\d+$/.test(text)) return;

            const pageNum = parseInt(text, 10);
            if (!Number.isFinite(pageNum)) return;

            if (pageNum > startPage && pageNum <= currentPage) {
                li.classList.add('active');
                if (el.tagName === 'A') {
                    const span = document.createElement('span');
                    span.className = 'page-link';
                    span.textContent = text;
                    el.replaceWith(span);
                }
            }
        });

        const nextLi = document.querySelector(this.selectors.pagination.next);
        if (nextLi) {
            const a = nextLi.querySelector('a.page-link');
            if (a) {
                const href = new URL(a.getAttribute('href'), window.location.href);
                href.searchParams.set('page', String(currentPage + 1));
                a.setAttribute('href', href.pathname + '?' + href.searchParams.toString());
            }
        }

        if (hasNext === false) {
            const nextLi = document.querySelector(this.selectors.pagination.next);
            const lastLi = document.querySelector(this.selectors.pagination.last);

            [nextLi, lastLi].forEach((li) => {
                if (!li || li.classList.contains('disabled')) return;
                li.classList.add('disabled');

                const a = li.querySelector('a.page-link');
                if (!a) return;

                const span = document.createElement('span');
                span.className = 'page-link';
                span.innerHTML = a.innerHTML;
                a.replaceWith(span);
            });
        }
    }

}

document.addEventListener('DOMContentLoaded', () => {
    new LoadMoreFavorites();
});
