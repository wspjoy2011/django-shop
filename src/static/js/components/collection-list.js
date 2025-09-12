import {ComponentFinder} from '../utils/broadcastManager.js';
import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {LoadingStateManager} from '../utils/components/LoadingStateManager.js';

class CollectionList extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'collection-updates'});

        this.selectors = {
            // Create Modal
            createButton: '.btn-create-list',
            createModal: '.collection-create-modal',
            createForm: '.collection-create-form',
            createCloseButton: '.collection-create-modal .modal-close',
            createSubmitButton: '.collection-create-modal .modal-submit',
            createCancelButton: '.collection-create-modal .modal-cancel',
            nameInput: '#collection-name',
            descriptionInput: '#collection-description',
            errorContainer: '.form-errors',

            // Delete Modal
            deleteModal: '.collection-delete-modal',
            deleteCloseButton: '.collection-delete-modal .modal-close',
            deleteCancelButton: '.collection-delete-modal .modal-cancel',
            deleteConfirmButton: '.modal-confirm-delete',
            deleteCollectionName: '#delete-collection-name',

            // Common
            overlay: '.modal-overlay',
            loadingSpinner: '.loading-spinner',
            collectionsGrid: '#collections-grid',
            emptyState: '.empty-state',
            card: '.col-lg-6.col-xl-4[data-collection-id]',
            actions: '.collection-actions',
            setDefaultButton: '.set-default-btn',
            deleteButton: '.delete-collection-btn',
        };

        this.cssClasses = {
            modalOpen: 'modal-open',
            hidden: 'hidden',
            show: 'show'
        };

        this.createUrl = '/api/v1/favorites/collections/';
        this.setDefaultUrl = '/api/v1/favorites/collections/{id}/set-default/';
        this.deleteUrl = '/api/v1/favorites/collections/{id}/';
        this.clearUrl = '/api/v1/favorites/collections/{id}/products/';

        this.httpClient = new AuthenticatedHttpClient();
        this.currentDeleteCollectionId = null;
        this.focusedElementBeforeModal = null;
        this.init();
    }

    init() {
        this.setupCreateModal();
        this.setupDeleteModal();
        super.init();
    }

    setupBroadcastSubscriptions() {
        this.broadcastManager.subscribe('collection_created', this.handleRemoteCollectionCreated.bind(this));
        this.broadcastManager.subscribe('collection_updated', this.handleCollectionUpdatedMessage.bind(this));
        this.broadcastManager.subscribe('default_collection_set', this.handleDefaultCollectionSetMessage.bind(this));
        this.broadcastManager.subscribe('collection_deleted', this.handleRemoteCollectionDeleted.bind(this));
    }

    setupAuthBroadcastSubscriptions() {
        this.authBroadcastManager.subscribe('logout_detected', this.handleLogoutMessage.bind(this));
    }

    handleRemoteCollectionCreated(data) {
        const {collection} = data;
        if (!collection) return;
        const existingCard = ComponentFinder.findByCollectionId(collection.id, this.selectors.card)[0];
        if (existingCard) return;
        this.addCollectionToGrid(collection);
    }

    handleCollectionUpdatedMessage(data) {
        const {collection} = data;
        if (!collection) return;
        const existingCard = ComponentFinder.findByCollectionId(collection.id, this.selectors.card)[0];
        if (existingCard) {
            this.updateExistingCollectionCard(existingCard, collection);
        }
    }

    handleDefaultCollectionSetMessage(data) {
        const {newDefaultId} = data;
        if (newDefaultId) {
            this.updateAllCollectionsAfterDefaultChange(newDefaultId);
            this.sortCollectionCards();
        }
    }

    handleRemoteCollectionDeleted(data) {
        const {collectionId} = data;
        if (collectionId) {
            this.removeCollectionFromGrid(collectionId);
            this.sortCollectionCards();
        }
    }

    handleLogoutMessage() {
        this.closeCreateModal();
        this.closeDeleteModal();
        const allCards = document.querySelectorAll(this.selectors.card);
        allCards.forEach(card => {
            AuthenticationHandler.resetAuthenticationState(card);
            const actions = card.querySelector(this.selectors.actions);
            if (actions) {
                actions.innerHTML = '';
            }
        });
        const createButton = document.querySelector(this.selectors.createButton);
        if (createButton) {
            createButton.style.display = 'none';
        }
    }

    handleLogoutDetection() {
        this.handleLogoutMessage();
        const redirectUrl = `/accounts/login/?next=/favorites/collections/`;
        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: redirectUrl,
            redirectTimeout: 3000
        });
    }

    broadcastCollectionCreated(collection) {
        this.broadcastManager.broadcast('collection_created', {collection});
    }

    broadcastCollectionDefaultSet(collectionId) {
        this.broadcastManager.broadcast('default_collection_set', {newDefaultId: collectionId});
    }

    broadcastCollectionDeleted(collectionId, collectionName) {
        this.broadcastManager.broadcast('collection_deleted', {collectionId, collectionName});
    }

    setupCreateModal() {
        this.createModal = document.querySelector(this.selectors.createModal);
        if (!this.createModal) {
            console.error('Collection create modal not found in DOM');
        }
    }

    setupDeleteModal() {
        this.deleteModal = document.querySelector(this.selectors.deleteModal);
        if (!this.deleteModal) {
            console.error('Collection delete modal not found in DOM');
        }
    }

    bindEvents() {
        super.bindEvents();
        document.addEventListener('click', (e) => {
            const setDefaultButton = e.target.closest(this.selectors.setDefaultButton);
            const deleteButton = e.target.closest(this.selectors.deleteButton);
            const component = e.target.closest(this.selectors.card);

            if (e.target.closest(this.selectors.createButton)) {
                e.preventDefault();
                this.openCreateModal();
            } else if (setDefaultButton && component) {
                e.preventDefault();
                const collectionId = setDefaultButton.getAttribute('data-collection-id');
                if (collectionId) {
                    void this.handleSetDefaultCollection(component, collectionId, setDefaultButton);
                }
            } else if (deleteButton && component) {
                e.preventDefault();
                const collectionId = component.getAttribute('data-collection-id');
                if (collectionId) {
                    void this.handleDeleteCollection(component, collectionId);
                }
            }
        });

        if (this.createModal) {
            this.createModal.addEventListener('click', (e) => {
                if (e.target.closest(this.selectors.createCloseButton) || e.target.closest(this.selectors.createCancelButton) || e.target.classList.contains('modal-overlay')) {
                    e.preventDefault();
                    this.closeCreateModal();
                }
            });
            this.createModal.querySelector(this.selectors.createForm)?.addEventListener('submit', (e) => {
                e.preventDefault();
                void this.handleCreateFormSubmit();
            });
            const textarea = this.createModal.querySelector(this.selectors.descriptionInput);
            if (textarea) {
                textarea.addEventListener('input', () => {
                    textarea.style.height = 'auto';
                    textarea.style.height = `${textarea.scrollHeight}px`;
                });
            }
        }

        if (this.deleteModal) {
            this.deleteModal.addEventListener('click', (e) => {
                if (e.target.closest(this.selectors.deleteCloseButton) || e.target.closest(this.selectors.deleteCancelButton) || e.target.classList.contains('modal-overlay')) {
                    e.preventDefault();
                    this.closeDeleteModal();
                } else if (e.target.closest(this.selectors.deleteConfirmButton)) {
                    e.preventDefault();
                    void this.handleDeleteConfirm();
                }
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.createModal && !this.createModal.classList.contains(this.cssClasses.hidden)) {
                    this.closeCreateModal();
                } else if (this.deleteModal && !this.deleteModal.classList.contains(this.cssClasses.hidden)) {
                    this.closeDeleteModal();
                }
            }
        });
    }

    async handleSetDefaultCollection(component, collectionId, button) {
        const url = this.setDefaultUrl.replace('{id}', collectionId);
        const originalIcon = button.querySelector('i');
        const originalClass = originalIcon.className;
        originalIcon.className = 'fas fa-spinner fa-spin text-muted';
        button.disabled = true;

        try {
            await this.httpClient.handleResponse(
                await this.httpClient.sendJSON(url, {}),
                component,
                {
                    onLoginRedirect: () => this.handleLogoutDetection(),
                    onSuccess: (data) => {
                        if (data.success) {
                            this.handleSetDefaultSuccess(collectionId, data.message);
                        } else {
                            MessageManager.showGlobalMessage(data.message || 'Failed to set collection as default', 'error');
                        }
                    },
                    onError: (error) => {
                        MessageManager.showGlobalMessage('Network error. Please try again.', 'error');
                    }
                }
            );
        } catch (error) {
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection();
            } else {
                MessageManager.showGlobalMessage('Network error. Please try again.', 'error');
            }
        } finally {
            originalIcon.className = originalClass;
            button.disabled = false;
        }
    }

    async handleDeleteCollection(component, collectionId) {
        const deleteUrl = this.deleteUrl.replace('{id}', collectionId);
        const collectionName = this.getCollectionNameFromTitle(component.querySelector('.collection-title'));

        try {
            const response = await this.httpClient.sendRequest(deleteUrl, {method: 'DELETE'});

            if (response.ok) {
                this.removeCollectionFromGrid(collectionId);
                this.sortCollectionCards();
                MessageManager.showGlobalMessage(`Collection "${collectionName}" has been deleted successfully.`, 'success');
                this.broadcastCollectionDeleted(collectionId, collectionName);
            } else if (response.status === 409) {
                this.currentDeleteCollectionId = collectionId;
                const collectionNameElement = this.deleteModal.querySelector(this.selectors.deleteCollectionName);
                if (collectionNameElement) {
                    collectionNameElement.textContent = collectionName;
                }
                this.openDeleteModal();
            } else {
                const errorData = await response.json();
                MessageManager.showGlobalMessage(errorData.message || 'Failed to delete collection.', 'error');
            }
        } catch (error) {
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection();
            } else {
                MessageManager.showGlobalMessage('A network error occurred while trying to delete the collection.', 'error');
            }
        }
    }

    async handleDeleteConfirm() {
        if (!this.currentDeleteCollectionId) return;

        const collectionId = this.currentDeleteCollectionId;
        const deleteUrl = this.deleteUrl.replace('{id}', collectionId);
        const clearUrl = this.clearUrl.replace('{id}', collectionId);

        const collectionCard = ComponentFinder.findByCollectionId(collectionId, this.selectors.card)[0];
        const collectionName = collectionCard ? this.getCollectionNameFromTitle(collectionCard.querySelector('.collection-title')) : 'Collection';

        this.setDeleteModalLoadingState(true);

        try {
            const clearResponse = await this.httpClient.sendRequest(clearUrl, {method: 'DELETE'});
            if (!clearResponse.ok) {
                throw new Error('Failed to clear items from the collection.');
            }

            const deleteResponse = await this.httpClient.sendRequest(deleteUrl, {method: 'DELETE'});
            if (!deleteResponse.ok) {
                throw new Error('Failed to delete the collection after clearing it.');
            }

            this.removeCollectionFromGrid(collectionId);
            this.sortCollectionCards();
            MessageManager.showGlobalMessage(`Collection "${collectionName}" has been deleted successfully.`, 'success');
            this.broadcastCollectionDeleted(collectionId, collectionName);
            this.closeDeleteModal();

        } catch (error) {
            console.error('Failed to confirm and delete collection:', error);
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection();
            } else {
                MessageManager.showGlobalMessage(error.message || 'Failed to delete collection. Please try again.', 'error');
                this.closeDeleteModal();
            }
        } finally {
            this.setDeleteModalLoadingState(false);
        }
    }

    handleSetDefaultSuccess(collectionId, message) {
        this.updateAllCollectionsAfterDefaultChange(collectionId);
        this.sortCollectionCards();
        MessageManager.showGlobalMessage(message, 'success');
        this.broadcastCollectionDefaultSet(collectionId);
    }

    updateAllCollectionsAfterDefaultChange(newDefaultCollectionId) {
        const allCollectionCards = document.querySelectorAll(this.selectors.card);
        allCollectionCards.forEach(card => {
            const cardId = card.getAttribute('data-collection-id');
            const titleElement = card.querySelector('.collection-title');
            if (!titleElement) return;
            const collectionName = this.getCollectionNameFromTitle(titleElement);
            this.rebuildCollectionTitle(titleElement, cardId, cardId === newDefaultCollectionId, collectionName);
        });
        this.removeOrphanSetDefaultButtons();
    }

    rebuildCollectionTitle(titleElement, collectionId, isDefault, collectionName) {
        if (!titleElement) return;
        while (titleElement.firstChild) {
            titleElement.removeChild(titleElement.firstChild);
        }
        titleElement.appendChild(document.createTextNode(collectionName.trim()));
        if (isDefault) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary ms-2';
            badge.textContent = 'Default';
            titleElement.appendChild(badge);
        } else {
            const actions = document.createElement('span');
            actions.className = 'collection-actions';
            const starButton = document.createElement('button');
            starButton.type = 'button';
            starButton.className = 'btn btn-link p-0 ms-2 set-default-btn';
            starButton.setAttribute('data-collection-id', String(collectionId));
            starButton.title = 'Set as default collection';
            starButton.innerHTML = '<i class="fas fa-star text-muted"></i>';
            actions.appendChild(starButton);
            const deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.className = 'btn btn-link p-0 ms-2 delete-collection-btn';
            deleteButton.setAttribute('data-collection-id', String(collectionId));
            deleteButton.title = 'Delete collection';
            deleteButton.innerHTML = '<i class="fas fa-trash-alt text-muted"></i>';
            actions.appendChild(deleteButton);
            titleElement.appendChild(actions);
        }
    }

    getCollectionNameFromTitle(titleElement) {
        if (!titleElement) return '';
        for (const node of titleElement.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                return node.textContent.trim();
            }
        }
        return titleElement.textContent.replace(/Default/g, '').trim();
    }

    removeCollectionFromGrid(collectionId) {
        const collectionCard = ComponentFinder.findByCollectionId(collectionId, this.selectors.card)[0];
        if (collectionCard) {
            collectionCard.remove();
        }

        const remainingCards = document.querySelectorAll(this.selectors.card);
        if (remainingCards.length === 0) {
            this.showEmptyState();
        }
    }

    showEmptyState() {
        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;

        const emptyStateHtml = `
            <div class="empty-state text-center py-5">
                <i class="fas fa-heart fa-4x text-muted mb-4"></i>
                <h3 class="text-muted mb-3">You don't have any favorite lists yet</h3>
                <p class="text-muted mb-4">Create your first list and add your favorite products</p>
                <div class="d-flex gap-3 justify-content-center">
                    <a href="/catalog/" class="btn btn-browse-products">
                        <i class="fas fa-search me-2"></i>Browse Products
                    </a>
                    <button type="button" class="btn btn-create-list">
                        <i class="fas fa-plus me-2"></i>Create List
                    </button>
                </div>
            </div>
        `;

        grid.outerHTML = emptyStateHtml;
    }

    addCollectionToGrid(collection) {
        const emptyState = document.querySelector(this.selectors.emptyState);
        if (emptyState) {
            const grid = this.buildGridContainer();
            grid.classList.add('mb-5');
            emptyState.replaceWith(grid);
        }
        this.ensureGridExists();
        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;

        if (collection.is_default) {
            this.removeDefaultBadgeFromAllCollections();
        }

        const existingCard = ComponentFinder.findByCollectionId(collection.id, this.selectors.card)[0];
        if (existingCard) {
            this.updateExistingCollectionCard(existingCard, collection);
        } else {
            const newCard = this.renderCollectionCard(collection);
            if (newCard) {
                grid.appendChild(newCard);
                this.animateNewCard(newCard);
            }
        }
        this.sortCollectionCards();
        this.removeOrphanSetDefaultButtons();
    }

    removeDefaultBadgeFromAllCollections() {
        const allCollectionCards = document.querySelectorAll(this.selectors.card);
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

    removeOrphanSetDefaultButtons() {
        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;
        const orphanButtons = Array.from(grid.children).filter(el => el.matches && el.matches('.set-default-btn'));
        if (orphanButtons.length > 0) {
            orphanButtons.forEach(btn => btn.remove());
        }
    }

    updateExistingCollectionCard(cardElement, collection) {
        if (!cardElement || !collection) return;

        cardElement.setAttribute('data-collection-id', String(collection.id));
        cardElement.dataset.authenticated = 'true';

        this.rebuildCollectionTitle(cardElement.querySelector('.collection-title'), collection.id, collection.is_default, collection.name);

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

    cloneExistingCard(existingCard, collection) {
        const clonedCard = existingCard.cloneNode(true);
        this.updateExistingCollectionCard(clonedCard, collection);

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
            if (headerEl) {
                headerEl.insertAdjacentElement('afterend', emptyElement);
            } else {
                clonedCard.querySelector('.collection-card')?.appendChild(emptyElement);
            }
        }
        emptyElement.style.display = 'block';

        return clonedCard;
    }

    renderCollectionCard(collection) {
        const existingCard = document.querySelector(this.selectors.card);
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
        console.error('Cannot render card: No existing card or template found.');
        return null;
    }

    openCreateModal() {
        if (!this.createModal) return;
        this.focusedElementBeforeModal = document.activeElement;
        this.createModal.classList.remove(this.cssClasses.hidden);
        this.createModal.removeAttribute('aria-hidden');
        document.body.classList.add(this.cssClasses.modalOpen);
        this.clearCreateForm();
        this.clearCreateMessages();
        const form = this.createModal.querySelector(this.selectors.createForm);
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
            this.createModal.querySelector(this.selectors.nameInput)?.focus();
        }, 100);
    }

    closeCreateModal() {
        if (!this.createModal) return;
        this.createModal.classList.add(this.cssClasses.hidden);
        this.createModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove(this.cssClasses.modalOpen);
        this.clearCreateForm();
        this.clearCreateMessages();
        if (this.focusedElementBeforeModal) {
            this.focusedElementBeforeModal.focus();
            this.focusedElementBeforeModal = null;
        }
    }

    openDeleteModal() {
        if (!this.deleteModal) return;
        this.focusedElementBeforeModal = document.activeElement;
        this.deleteModal.classList.remove(this.cssClasses.hidden);
        this.deleteModal.removeAttribute('aria-hidden');
        document.body.classList.add(this.cssClasses.modalOpen);
        setTimeout(() => {
            this.deleteModal.querySelector(this.selectors.deleteConfirmButton)?.focus();
        }, 100);
    }

    closeDeleteModal() {
        if (!this.deleteModal) return;
        this.deleteModal.classList.add(this.cssClasses.hidden);
        this.deleteModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove(this.cssClasses.modalOpen);
        this.currentDeleteCollectionId = null;
        if (this.focusedElementBeforeModal) {
            this.focusedElementBeforeModal.focus();
            this.focusedElementBeforeModal = null;
        }
    }

    async handleCreateFormSubmit() {
        const formData = this.getCreateFormData();
        this.clearCreateMessages();
        this.setCreateModalLoadingState(true);
        try {
            await this.httpClient.handleResponse(
                await this.httpClient.sendJSON(this.createUrl, formData),
                this.createModal,
                {
                    onLoginRedirect: () => this.handleLogoutDetection(),
                    onSuccess: (data) => {
                        if (data.success) {
                            this.handleCreateSuccess(data);
                        } else {
                            this.handleCreateErrors(data.errors || {non_field_errors: ['Unknown error occurred']});
                        }
                    },
                    onError: (error) => {
                        this.handleCreateErrors({non_field_errors: ['Network error. Please try again.']});
                    }
                }
            );
        } catch (error) {
            console.error("Collection creation form submission failed:", error);
            if (AuthenticationHandler.isAuthenticationError(error)) {
                this.handleLogoutDetection();
            } else {
                this.handleCreateErrors({non_field_errors: ['A network error occurred. Please try again.']});
            }
        } finally {
            this.setCreateModalLoadingState(false);
        }
    }

    getCreateFormData() {
        const form = this.createModal.querySelector(this.selectors.createForm);
        const isEmptyState = !!document.querySelector(this.selectors.emptyState);

        return {
            name: form.name.value.trim(),
            description: form.description.value.trim(),
            is_public: form.is_public.checked,
            is_default: isEmptyState ? true : form.is_default.checked
        };
    }

    handleCreateSuccess(data) {
        const {collection, message} = data;
        if (!collection) {
            console.error("handleCreateSuccess called but no collection found in data:", data);
            this.handleCreateErrors({non_field_errors: ['Invalid response from server.']});
            return;
        }
        MessageManager.showGlobalMessage(message || `Collection "${collection.name}" created successfully.`, 'success');

        this.addCollectionToGrid(collection);
        this.broadcastCollectionCreated(collection);
        this.closeCreateModal();
    }

    handleCreateErrors(errors) {
        Object.keys(errors).forEach((field) => {
            const fieldError = this.createModal.querySelector(`[data-field="${field}"]`);
            if (fieldError) {
                fieldError.textContent = errors[field][0];
                fieldError.classList.add(this.cssClasses.show);
            }
        });
        if (errors.non_field_errors) {
            this.showCreateErrorMessage(errors.non_field_errors[0]);
        }
    }

    setCreateModalLoadingState(isLoading) {
        LoadingStateManager.setModalLoadingState(
            this.createModal,
            isLoading,
            {
                submitButton: this.selectors.createSubmitButton,
                loadingSpinner: this.selectors.loadingSpinner
            },
            this.cssClasses
        );
    }


    setDeleteModalLoadingState(isLoading) {
        const confirmButton = this.deleteModal.querySelector(this.selectors.deleteConfirmButton);
        if (!confirmButton) return;
        const spinner = confirmButton.querySelector('.loading-spinner');
        const btnText = confirmButton.querySelector('.btn-text');

        if (isLoading) {
            confirmButton.disabled = true;
            spinner?.classList.remove(this.cssClasses.hidden);
            if (btnText) btnText.style.opacity = '0.7';
        } else {
            confirmButton.disabled = false;
            spinner?.classList.add(this.cssClasses.hidden);
            if (btnText) btnText.style.opacity = '1';
        }
    }

    showCreateErrorMessage(message) {
        const errorContainer = this.createModal?.querySelector(this.selectors.errorContainer);
        if (errorContainer) {
            errorContainer.className = 'form-errors error';
            errorContainer.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${MessageManager.escapeHtml(message)}`;
        }
    }

    sortCollectionCards() {
        const grid = document.querySelector(this.selectors.collectionsGrid);
        if (!grid) return;
        const cards = Array.from(grid.querySelectorAll(this.selectors.card));
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

    clearCreateForm() {
        const form = this.createModal?.querySelector(this.selectors.createForm);
        if (!form) return;
        form.reset();
        const textarea = form.querySelector(this.selectors.descriptionInput);
        if (textarea) {
            textarea.style.height = 'auto';
        }
    }

    clearCreateMessages() {
        if (!this.createModal) return;
        this.createModal.querySelectorAll('.field-error').forEach((error) => {
            error.textContent = '';
            error.classList.remove(this.cssClasses.show);
        });
        const errorContainer = this.createModal.querySelector(this.selectors.errorContainer);
        if (errorContainer) {
            errorContainer.className = 'form-errors';
            errorContainer.innerHTML = '';
            errorContainer.classList.add(this.cssClasses.hidden);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionList();
});
