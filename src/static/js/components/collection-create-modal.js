import { getCookie } from '../utils/httpAuth.js';

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
        this.setupModal();
        this.bindEvents();
    }

    setupCSRF() {
        this.csrfToken = getCookie('csrftoken');
    }

    setupModal() {
        this.modal = document.querySelector(this.selectors.modal);

        if (!this.modal) {
            console.error('Collection create modal not found in DOM');
            return;
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

            this.modal.querySelector(this.selectors.form).addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmit();
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

        setTimeout(() => {
            this.modal.querySelector(this.selectors.nameInput)?.focus();
        }, 100);

        this.clearForm();
        this.clearErrors();
    }

    closeModal() {
        if (!this.modal) return;

        this.modal.classList.add(this.cssClasses.hidden);
        document.body.classList.remove(this.cssClasses.modalOpen);

        this.clearForm();
        this.clearErrors();
    }

    async handleFormSubmit() {
        const formData = this.getFormData();

        this.clearErrors();
        this.setLoadingState(true);

        try {
            const response = await this.sendRequest(formData);
            const data = await response.json();

            if (response.ok && data.success) {
                this.handleSuccess(data.collection);
            } else {
                this.handleErrors(data.errors || { non_field_errors: ['Unknown error occurred'] });
            }
        } catch (_) {
            this.handleErrors({ non_field_errors: ['Network error. Please try again.'] });
        } finally {
            this.setLoadingState(false);
        }
    }

    getFormData() {
        const form = this.modal.querySelector(this.selectors.form);

        return {
            name: form.name.value.trim(),
            description: form.description.value.trim(),
            is_public: form.is_public.checked,
            is_default: form.is_default.checked
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
        const cardHTML = this.renderCollectionCard(collection);

        if (emptyState) {
            const grid = this.buildGridContainer();

            emptyState.replaceWith(grid);
            grid.insertAdjacentHTML('beforeend', cardHTML);

            const newCard = grid.lastElementChild;
            this.animateNewCard(newCard);

            return;
        }

        this.ensureGridExists();

        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;

        grid.insertAdjacentHTML('beforeend', cardHTML);

        const newCard = grid.lastElementChild;
        this.animateNewCard(newCard);
    }

    ensureGridExists() {
        if (!document.querySelector(this.selectors.collectionsGrid)) {
            const anchor = document.querySelector('.container .row .col-12');
            const grid = this.buildGridContainer();

            if (anchor && anchor.parentElement) {
                anchor.parentElement.insertAdjacentElement('beforeend', grid);
            } else {
                const containerRow = document.querySelector('.container .row') || document.body;
                containerRow.appendChild(grid);
            }
        }
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
            return this.processTemplate(templateScript.textContent, collection);
        }

        return '';
    }

    cloneExistingCard(existingCard, collection) {
        const clonedCard = existingCard.cloneNode(true);

        clonedCard.setAttribute('data-collection-id', collection.id);

        const titleElement = clonedCard.querySelector('.collection-title');
        if (titleElement) {
            titleElement.innerHTML = this.escapeHtml(collection.name);

            if (collection.is_default) {
                titleElement.innerHTML += '<span class="badge bg-primary ms-2">Default</span>';
            }
        }

        const itemsCountElement = clonedCard.querySelector('.collection-items-count');
        if (itemsCountElement) {
            itemsCountElement.textContent = `Items count: ${collection.total_items_count}`;
        }

        const updatedElement = clonedCard.querySelector('.collection-footer small');
        if (updatedElement) {
            updatedElement.textContent = `Updated: ${collection.formatted_updated_at}`;
        }

        const linkElement = clonedCard.querySelector('.btn-view-all');
        if (linkElement) {
            linkElement.href = collection.absolute_url || '#';
        }

        const sliderElement = clonedCard.querySelector('.collection-slider');
        let emptyElement = clonedCard.querySelector('.empty-collection');

        if (sliderElement) {
            sliderElement.remove();
        }

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
                clonedCard.appendChild(emptyElement);
            }
        } else {
            emptyElement.style.display = 'block';
        }

        return clonedCard.outerHTML;
    }

    processTemplate(templateContent, collection) {
        let html = templateContent;

        html = html.replace(/\{\{ collection\.id }}/g, collection.id);
        html = html.replace(/\{\{ collection\.name }}/g, this.escapeHtml(collection.name));
        html = html.replace(/\{\{ collection\.total_items_count }}/g, collection.total_items_count);
        html = html.replace(/\{\{ collection\.updated_at\|date:"M d, Y" }}/g, collection.formatted_updated_at);
        html = html.replace(/\{\{ collection\.absolute_url }}/g, collection.absolute_url || '#');

        if (collection.is_default) {
            html = html.replace(/\{% if collection\.is_default %}(.*?)\{% endif %}/gs, '$1');
        } else {
            html = html.replace(/\{% if collection\.is_default %}.*?\{% endif %}/gs, '');
        }

        html = html.replace(/\{% if collection\.slider_items %}.*?\{% else %}(.*?)\{% endif %}/gs, '$1');

        html = html.replace(/\{%.*?%}/g, '');
        html = html.replace(/\{\{.*?}}/g, '');

        return html;
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

    clearErrors() {
        if (!this.modal) return;

        this.modal.querySelectorAll('.field-error').forEach((error) => {
            error.textContent = '';
            error.classList.remove(this.cssClasses.show);
        });

        const errorContainer = this.modal.querySelector(this.selectors.errorContainer);
        if (errorContainer) {
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

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;

        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionCreateModal();
});
