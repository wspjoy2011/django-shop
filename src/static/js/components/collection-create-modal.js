import {getCookie, isLoginRedirectResponse, isLoginRedirectErrorLike} from '../utils/httpAuth.js';

class CollectionCreateModal {
    constructor() {
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

        this.init();
    }

    init() {
        this.setupCSRF();
        this.setupBroadcastChannel();
        this.setupModal();
        this.bindEvents();
    }

    setupCSRF() {
        this.csrfToken = getCookie('csrftoken');
    }

    setupBroadcastChannel() {
        if (typeof BroadcastChannel !== 'undefined') {
            this.broadcastChannel = new BroadcastChannel('collection-updates');
            this.broadcastChannel.addEventListener('message', (event) => {
                this.handleBroadcastMessage(event.data);
            });
        }
    }

    handleBroadcastMessage(data) {
        if (!data || !data.type) return;

        switch (data.type) {
            case 'collection_created':
                this.handleCollectionCreatedMessage(data);
                break;
            case 'collection_updated':
                this.handleCollectionUpdatedMessage(data);
                break;
            case 'logout_detected':
                this.handleLogoutMessage(data);
                break;
        }
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

        const existingCard = document.querySelector(`[data-collection-id="${collection.id}"]`);
        if (existingCard) {
            this.updateExistingCollectionCard(existingCard, collection);
        }
    }

    handleLogoutMessage(data) {
        this.closeModal();
        this.showErrorMessage('Session expired. Please log in again.');
    }

    broadcastCollectionCreated(collection) {
        if (!this.broadcastChannel) return;

        const message = {
            type: 'collection_created',
            collection: collection,
            timestamp: Date.now()
        };

        this.broadcastChannel.postMessage(message);
    }

    broadcastLogoutDetection() {
        if (!this.broadcastChannel) return;

        const message = {
            type: 'logout_detected',
            timestamp: Date.now()
        };

        this.broadcastChannel.postMessage(message);
    }

    setupModal() {
        this.modal = document.querySelector(this.selectors.modal);

        if (!this.modal) {
            console.error('Collection create modal not found in DOM');
        }
    }

    bindEvents() {
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

        window.addEventListener('beforeunload', () => {
            if (this.broadcastChannel) {
                this.broadcastChannel.close();
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
            const response = await this.sendRequest(formData);

            if (isLoginRedirectResponse(response)) {
                this.handleLogoutDetection(response.url);
                return;
            }

            const data = await response.json();

            if (response.ok && data.success) {
                this.handleSuccess(data.collection);
            } else {
                this.handleErrors(data.errors || {non_field_errors: ['Unknown error occurred']});
            }
        } catch (error) {
            if (isLoginRedirectErrorLike(error)) {
                this.handleLogoutDetection();
            } else {
                this.handleErrors({non_field_errors: ['Network error. Please try again.']});
            }
        } finally {
            this.setLoadingState(false);
        }
    }

    handleLogoutDetection(loginUrl = null) {
        this.broadcastLogoutDetection();
        this.closeModal();

        const message = loginUrl ? 'Session expired.' : 'Session expired. Please log in again.';
        this.showGlobalMessage(message, 'warning');
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

    async sendRequest(data) {
        return fetch(this.createUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
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

        const cardHTML = this.renderCollectionCard(collection);

        if (cardHTML) {
            const existingCard = grid.querySelector(`[data-collection-id="${collection.id}"]`);
            if (existingCard) {
                this.updateExistingCollectionCard(existingCard, collection);
                return;
            }

            grid.insertAdjacentHTML('beforeend', cardHTML);
            const newCard = grid.lastElementChild;
            this.animateNewCard(newCard);
        }
    }

    updateExistingCollectionCard(cardElement, collection) {
        if (!cardElement || !collection) return;

        cardElement.setAttribute('data-collection-id', collection.id);

        const titleElement = cardElement.querySelector('.collection-title');
        if (titleElement) {
            titleElement.innerHTML = this.escapeHtml(collection.name);

            if (collection.is_default) {
                titleElement.innerHTML += '<span class="badge bg-primary ms-2">Default</span>';
            }
        }

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
        if (titleElement) {
            const existingBadge = titleElement.querySelector('.badge');
            if (existingBadge) {
                existingBadge.remove();
            }

            const titleText = titleElement.childNodes[0];
            if (titleText) {
                titleText.textContent = collection.name;
            } else {
                titleElement.innerHTML = this.escapeHtml(collection.name);
            }

            if (collection.is_default) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-primary ms-2';
                badge.textContent = 'Default';
                titleElement.appendChild(badge);
            }
        }

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

    setLoadingState(isLoading) {
        if (!this.modal) return;

        const submitButton = this.modal.querySelector(this.selectors.submitButton);
        const spinner = this.modal.querySelector(this.selectors.loadingSpinner);

        if (submitButton) {
            submitButton.disabled = isLoading;
        }

        if (spinner) {
            spinner.classList.toggle(this.cssClasses.hidden, !isLoading);
        }
    }

    showSuccessMessage(message) {
        const errorContainer = this.modal?.querySelector(this.selectors.errorContainer);

        if (errorContainer) {
            errorContainer.className = 'form-errors success';
            errorContainer.innerHTML = `<i class="fas fa-check me-1"></i>${this.escapeHtml(message)}`;
        }
    }

    showErrorMessage(message) {
        const errorContainer = this.modal?.querySelector(this.selectors.errorContainer);

        if (errorContainer) {
            errorContainer.className = 'form-errors error';
            errorContainer.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${this.escapeHtml(message)}`;
        }
    }

    showGlobalMessage(message, type = 'info') {
        const messagesContainer = document.querySelector('.messages-container') ||
            document.querySelector('#messages') ||
            document.querySelector('.alert-container');

        if (messagesContainer) {
            const alertClass = type === 'warning' ? 'alert-warning' :
                type === 'error' ? 'alert-danger' : 'alert-info';

            const messageElement = document.createElement('div');
            messageElement.className = `alert ${alertClass} alert-dismissible fade show`;
            messageElement.innerHTML = `
                ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            messagesContainer.appendChild(messageElement);

            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.remove();
                }
            }, 5000);
        } else {
            console.warn('Global message:', message);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionCreateModal();
});
