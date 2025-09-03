import { ComponentFinder } from '../utils/broadcastManager.js';
import { BaseComponent } from '../utils/components/BaseComponent.js';
import { MessageManager } from '../utils/components/MessageManager.js';
import { AuthenticationHandler } from '../utils/components/AuthenticationHandler.js';
import { AuthenticatedHttpClient } from '../utils/http/AuthenticatedHttpClient.js';
import { LoadingStateManager } from '../utils/components/LoadingStateManager.js';

class CollectionCreateModal extends BaseComponent {
    constructor() {
        super({ broadcastChannelName: 'collection-updates' });

        this.selectors = {
            createButton: '.btn-create-list',
            modal: '.collection-create-modal',
            overlay: '.modal-overlay',
            form: '.collection-create-form',
            closeButton: '.modal-close',
            nameInput: '#collection-name',
            descriptionInput: '#collection-description',
            submitButton: '.modal-submit',
            cancelButton: '.modal-cancel',
            errorContainer: '.form-errors',
            loadingSpinner: '.loading-spinner',
            collectionsGrid: '#collections-grid',
            emptyState: '.empty-state'
        };

        this.cssClasses = {
            modalOpen: 'modal-open',
            hidden: 'hidden',
            show: 'show'
        };

        this.createUrl = '/favorites/collections/create/';
        this.httpClient = new AuthenticatedHttpClient();
        this.init();
    }

    init() {
        super.init();
        this.setupModal();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('collection_created', (data) => {
            this.handleCollectionCreatedMessage(data);
        });

        this.broadcastManager.subscribe('collection_updated', (data) => {
            this.handleCollectionUpdatedMessage(data);
        });

        this.broadcastManager.subscribe('logout_detected', (data) => {
            this.handleLogoutMessage(data);
        });
    }

    handleCollectionCreatedMessage(data) {
        const {collection} = data;
        if (!collection) return;

        const currentGrid = document.querySelector(this.selectors.collectionsGrid);
        const emptyState = document.querySelector(this.selectors.emptyState);

        if (currentGrid || emptyState) {
            this.addCollectionToGrid(collection);
        }
    }

    handleCollectionUpdatedMessage(data) {
        const {collection} = data;
        if (!collection) return;

        const existingCard = ComponentFinder.findByCollectionId(collection.id, '[data-collection-id]')[0];
        if (existingCard) {
            this.updateExistingCollectionCard(existingCard, collection);
        }
    }

    handleLogoutMessage(data) {
        this.closeModal();
        this.showErrorMessage('Session expired. Please log in again.');
    }

    broadcastCollectionCreated(collection) {
        this.broadcastManager.broadcast('collection_created', {
            collection: collection
        });
    }

    setupModal() {
        this.modal = document.querySelector(this.selectors.modal);

        if (!this.modal) {
            console.error('Collection create modal not found in DOM');
        }
    }

    bindEvents() {
        super.bindEvents();

        document.addEventListener('click', (e) => {
            if (e.target.closest(this.selectors.createButton)) {
                e.preventDefault();
                this.openModal();
            }
        });

        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (
                    e.target.closest(this.selectors.closeButton) ||
                    e.target.closest(this.selectors.cancelButton) ||
                    e.target.classList.contains('modal-overlay')
                ) {
                    e.preventDefault();
                    this.closeModal();
                }
            });

            this.modal.querySelector(this.selectors.form)?.addEventListener('submit', (e) => {
                e.preventDefault();
                void this.handleFormSubmit();
            });

            const textarea = this.modal.querySelector(this.selectors.descriptionInput);
            if (textarea) {
                textarea.addEventListener('input', () => {
                    textarea.style.height = 'auto';
                    textarea.style.height = textarea.scrollHeight + 'px';
                });
            }
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal?.classList.contains(this.cssClasses.hidden)) {
                this.closeModal();
            }
        });
    }

    openModal() {
        if (!this.modal) return;

        this.modal.classList.remove(this.cssClasses.hidden);
        document.body.classList.add(this.cssClasses.modalOpen);

        this.clearForm();
        this.clearMessages();

        const form = this.modal.querySelector(this.selectors.form);
        const isEmptyState = !!document.querySelector(this.selectors.emptyState);
        if (form && form.is_default) {
            if (isEmptyState) {
                form.is_default.checked = true;
                form.is_default.disabled = true;
            } else {
                form.is_default.disabled = false;
            }
        }

        setTimeout(() => {
            this.modal.querySelector(this.selectors.nameInput)?.focus();
        }, 100);
    }

    closeModal() {
        if (!this.modal) return;

        this.modal.classList.add(this.cssClasses.hidden);
        document.body.classList.remove(this.cssClasses.modalOpen);

        this.clearForm();
        this.clearMessages();
    }

    async handleFormSubmit() {
        const formData = this.getFormData();

        this.clearMessages();
        this.setLoadingState(true);

        try {
            const result = await this.httpClient.handleResponse(
                await this.httpClient.sendJSON(this.createUrl, formData),
                null,
                {
                    onLoginRedirect: (loginUrl) => this.handleLogoutDetection(loginUrl),
                    onSuccess: (data) => {
                        if (data.success) {
                            this.handleSuccess(data.collection);
                        } else {
                            this.handleErrors(data.errors || {non_field_errors: ['Unknown error occurred']});
                        }
                    },
                    onError: () => {
                        this.handleErrors({non_field_errors: ['Network error. Please try again.']});
                    }
                }
            );

        } catch (error) {
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection();
            } else {
                this.handleErrors({non_field_errors: ['Network error. Please try again.']});
            }
        } finally {
            this.setLoadingState(false);
        }
    }

    handleLogoutDetection(loginUrl = null) {
        this.broadcastManager.broadcast('logout_detected', {});
        this.closeModal();

        const message = loginUrl ? 'Session expired.' : 'Session expired. Please log in again.';
        MessageManager.showGlobalMessage(message, 'warning');
    }

    getFormData() {
        const form = this.modal.querySelector(this.selectors.form);
        const isEmptyState = !!document.querySelector(this.selectors.emptyState);

        return {
            name: form.name.value.trim(),
            description: form.description.value.trim(),
            is_public: form.is_public.checked,
            is_default: isEmptyState ? true : form.is_default.checked
        };
    }

    handleSuccess(collection) {
        this.showSuccessMessage('Collection created successfully!');
        this.broadcastCollectionCreated(collection);
        this.addCollectionToGrid(collection);

        setTimeout(() => {
            this.closeModal();
        }, 1500);
    }

    handleErrors(errors) {
        Object.keys(errors).forEach((field) => {
            const fieldError = this.modal.querySelector(`[data-field="${field}"]`);

            if (fieldError) {
                fieldError.textContent = errors[field][0];
                fieldError.classList.add(this.cssClasses.show);
            }
        });

        if (errors.non_field_errors) {
            this.showErrorMessage(errors.non_field_errors[0]);
        }
    }

    setLoadingState(isLoading) {
        LoadingStateManager.setModalLoadingState(this.modal, isLoading, this.selectors, this.cssClasses);
    }

    showSuccessMessage(message) {
        const errorContainer = this.modal?.querySelector(this.selectors.errorContainer);

        if (errorContainer) {
            errorContainer.className = 'form-errors success';
            errorContainer.innerHTML = `<i class="fas fa-check me-1"></i>${MessageManager.escapeHtml(message)}`;
        }
    }

    showErrorMessage(message) {
        const errorContainer = this.modal?.querySelector(this.selectors.errorContainer);

        if (errorContainer) {
            errorContainer.className = 'form-errors error';
            errorContainer.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${MessageManager.escapeHtml(message)}`;
        }
    }

    sortCollectionCards() {
        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;

        const cards = Array.from(grid.querySelectorAll('[data-collection-id]'));
        if (cards.length <= 1) return;

        cards.sort((a, b) => {
            const aIsDefault = this.getCollectionIsDefault(a);
            const bIsDefault = this.getCollectionIsDefault(b);
            const aUpdatedAt = this.getCollectionUpdatedAt(a);
            const bUpdatedAt = this.getCollectionUpdatedAt(b);

            if (aIsDefault !== bIsDefault) {
                return bIsDefault - aIsDefault;
            }

            return new Date(bUpdatedAt) - new Date(aUpdatedAt);
        });

        cards.forEach(card => {
            grid.appendChild(card);
        });
    }

    getCollectionIsDefault(cardElement) {
        const titleElement = cardElement.querySelector('.collection-title');
        if (!titleElement) return false;

        const badge = titleElement.querySelector('.badge');
        return badge && badge.textContent.trim() === 'Default';
    }

    getCollectionUpdatedAt(cardElement) {
        const updatedElement = cardElement.querySelector('.collection-footer small');
        if (!updatedElement) return new Date().toISOString();

        const text = updatedElement.textContent;
        const match = text.match(/Updated: (.+)/);
        if (match && match[1] !== 'Now') {
            try {
                return new Date(match[1]).toISOString();
            } catch (e) {
                return new Date().toISOString();
            }
        }

        return new Date().toISOString();
    }

    addCollectionToGrid(collection) {
        const emptyState = document.querySelector(this.selectors.emptyState);

        if (emptyState) {
            const grid = this.buildGridContainer();
            grid.classList.add('mb-5');
            emptyState.replaceWith(grid);

            const cardHTML = this.renderCollectionCard(collection);
            if (cardHTML) {
                grid.insertAdjacentHTML('beforeend', cardHTML);
                const newCard = grid.lastElementChild;
                this.animateNewCard(newCard);
            }
            return;
        }

        this.ensureGridExists();

        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;

        if (collection.is_default) {
            this.removeDefaultBadgeFromAllCollections();
        }

        const cardHTML = this.renderCollectionCard(collection);

        if (cardHTML) {
            const existingCard = ComponentFinder.findByCollectionId(collection.id, '[data-collection-id]')[0];
            if (existingCard) {
                this.updateExistingCollectionCard(existingCard, collection);
                this.sortCollectionCards();
                return;
            }

            grid.insertAdjacentHTML('beforeend', cardHTML);
            const newCard = grid.lastElementChild;

            this.sortCollectionCards();
            this.animateNewCard(newCard);
        }
    }

    removeDefaultBadgeFromAllCollections() {
        const allCollectionCards = document.querySelectorAll('[data-collection-id]');

        allCollectionCards.forEach(card => {
            const titleElement = card.querySelector('.collection-title');
            if (titleElement) {
                const badge = titleElement.querySelector('.badge');
                if (badge && badge.textContent.trim() === 'Default') {
                    badge.remove();
                }
            }
        });
    }

    updateCollectionTitle(titleElement, collection) {
        if (!titleElement) return;

        const existingBadge = titleElement.querySelector('.badge');
        if (existingBadge) {
            existingBadge.remove();
        }

        const titleText = titleElement.childNodes[0];
        if (titleText) {
            titleText.textContent = collection.name;
        } else {
            titleElement.innerHTML = MessageManager.escapeHtml(collection.name);
        }

        if (collection.is_default) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary ms-2';
            badge.textContent = 'Default';
            titleElement.appendChild(badge);
        }
    }

    updateExistingCollectionCard(cardElement, collection) {
        if (!cardElement || !collection) return;

        cardElement.setAttribute('data-collection-id', collection.id);

        const titleElement = cardElement.querySelector('.collection-title');
        this.updateCollectionTitle(titleElement, collection);

        const itemsCountElement = cardElement.querySelector('.collection-items-count');
        if (itemsCountElement) {
            itemsCountElement.textContent = `Items count: ${collection.total_items_count || 0}`;
        }

        const updatedElement = cardElement.querySelector('.collection-footer small');
        if (updatedElement) {
            updatedElement.textContent = `Updated: ${collection.formatted_updated_at || 'Now'}`;
        }

        const linkElement = cardElement.querySelector('.btn-view-all');
        if (linkElement) {
            linkElement.href = collection.absolute_url || '#';
        }

        this.animateUpdatedCard(cardElement);
    }

    ensureGridExists() {
        if (document.querySelector(this.selectors.collectionsGrid)) {
            return;
        }

        const possibleAnchors = [
            '.container .row .col-12',
            '.container .row',
            '.container',
            'main'
        ];

        let targetElement = null;
        for (const selector of possibleAnchors) {
            targetElement = document.querySelector(selector);
            if (targetElement) break;
        }

        if (!targetElement) return;

        const grid = this.buildGridContainer();
        targetElement.appendChild(grid);
    }

    buildGridContainer() {
        const grid = document.createElement('div');
        grid.className = 'row g-4';
        grid.id = 'collections-grid';
        return grid;
    }

    renderCollectionCard(collection) {
        const existingCard = document.querySelector('[data-collection-id]');
        if (existingCard) {
            return this.cloneExistingCard(existingCard, collection);
        }

        const templateScript = document.getElementById('collection-card-template');
        if (templateScript) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = templateScript.textContent.trim();
            const templateCard = tempDiv.firstElementChild;

            if (templateCard) {
                return this.cloneExistingCard(templateCard, collection);
            }
        }

        return '';
    }

    cloneExistingCard(existingCard, collection) {
        const clonedCard = existingCard.cloneNode(true);

        clonedCard.setAttribute('data-collection-id', collection.id);

        const titleElement = clonedCard.querySelector('.collection-title');
        this.updateCollectionTitle(titleElement, collection);

        const itemsCountElement = clonedCard.querySelector('.collection-items-count');
        if (itemsCountElement) {
            itemsCountElement.textContent = `Items count: ${collection.total_items_count || 0}`;
        }

        const updatedElement = clonedCard.querySelector('.collection-footer small');
        if (updatedElement) {
            updatedElement.textContent = `Updated: ${collection.formatted_updated_at || 'Now'}`;
        }

        const linkElement = clonedCard.querySelector('.btn-view-all');
        if (linkElement) {
            linkElement.href = collection.absolute_url || '#';
        }

        const sliderElement = clonedCard.querySelector('.collection-slider');
        if (sliderElement) {
            sliderElement.remove();
        }

        let emptyElement = clonedCard.querySelector('.empty-collection');
        if (!emptyElement) {
            emptyElement = document.createElement('div');
            emptyElement.className = 'empty-collection';
            emptyElement.innerHTML = `
                <div class="text-center py-5">
                  <i class="fas fa-heart-broken fa-3x text-muted mb-3"></i>
                  <p class="text-muted">Collection is empty</p>
                  <a href="/catalog/" class="btn btn-sm btn-outline-primary">Add Products</a>
                </div>
            `;

            const headerEl = clonedCard.querySelector('.collection-header');
            const footerEl = clonedCard.querySelector('.collection-footer');

            if (footerEl) {
                footerEl.parentNode.insertBefore(emptyElement, footerEl);
            } else if (headerEl && headerEl.parentNode) {
                headerEl.parentNode.appendChild(emptyElement);
            } else {
                const cardEl = clonedCard.querySelector('.collection-card');
                if (cardEl) {
                    cardEl.appendChild(emptyElement);
                }
            }
        } else {
            emptyElement.style.display = 'block';
        }

        return clonedCard.outerHTML;
    }

    animateNewCard(cardElement) {
        if (!cardElement) return;

        cardElement.style.opacity = '0';
        cardElement.style.transform = 'translateY(20px)';

        setTimeout(() => {
            cardElement.style.transition = 'all 0.3s ease';
            cardElement.style.opacity = '1';
            cardElement.style.transform = 'translateY(0)';
        }, 50);
    }

    animateUpdatedCard(cardElement) {
        if (!cardElement) return;

        cardElement.style.transform = 'scale(1.02)';
        cardElement.style.transition = 'transform 0.2s ease';

        setTimeout(() => {
            cardElement.style.transform = 'scale(1)';
        }, 200);
    }

    clearForm() {
        if (!this.modal) return;

        const form = this.modal.querySelector(this.selectors.form);
        if (!form) return;

        form.name.value = '';
        form.description.value = '';
        form.is_public.checked = false;
        form.is_default.checked = false;

        const textarea = form.description;
        if (textarea) {
            textarea.style.height = 'auto';
        }
    }

    clearMessages() {
        if (!this.modal) return;

        this.modal.querySelectorAll('.field-error').forEach((error) => {
            error.textContent = '';
            error.classList.remove(this.cssClasses.show);
        });

        const errorContainer = this.modal.querySelector(this.selectors.errorContainer);
        if (errorContainer) {
            errorContainer.className = 'form-errors';
            errorContainer.innerHTML = '';
            errorContainer.classList.add(this.cssClasses.hidden);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionCreateModal();
});
