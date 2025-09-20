import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';

class CollectionReorderHandler extends BaseComponent {
    constructor() {
        super();

        this.selectors = {
            grid: '#collection-items-grid',
            item: '.draggable-item',
            card: '.favorite-card',
            dragHandle: '.drag-handle'
        };

        this.cssClasses = {
            dragging: 'dragging',
            dragOver: 'drag-over',
            placeholder: 'drag-placeholder',
            canReorder: 'can-reorder'
        };

        this.reorderUrl = '/api/v1/favorites/collections/{id}/reorder/';

        this.dragState = {
            draggedItem: null,
            draggedIndex: -1,
            placeholder: null,
            items: []
        };

        this.httpClient = new AuthenticatedHttpClient();
        this.init();
    }

    bindEvents() {
        super.bindEvents();

        const grid = document.querySelector(this.selectors.grid);
        if (!grid || grid.dataset.canReorder !== 'true') {
            return;
        }

        grid.classList.add(this.cssClasses.canReorder);

        document.addEventListener('mousedown', (e) => {
            if (e.target.closest(this.selectors.dragHandle)) {
                const item = e.target.closest(this.selectors.item);
                if (item) {
                    e.preventDefault();
                    this.startDrag(item, e);
                }
            }
        });

        document.addEventListener('touchstart', (e) => {
            if (e.target.closest(this.selectors.dragHandle)) {
                const item = e.target.closest(this.selectors.item);
                if (item) {
                    e.preventDefault();
                    this.startDrag(item, e.touches[0]);
                }
            }
        }, {passive: false});

        document.addEventListener('mousemove', (e) => this.handleDrag(e));
        document.addEventListener('mouseup', (e) => this.endDrag(e));
        document.addEventListener('touchmove', (e) => this.handleDrag(e.touches[0]), {passive: false});
        document.addEventListener('touchend', (e) => this.endDrag(e));
    }

    startDrag(item, event) {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return;

        this.dragState.draggedItem = item;
        this.dragState.items = Array.from(grid.querySelectorAll(this.selectors.item));
        this.dragState.draggedIndex = this.dragState.items.indexOf(item);

        this.createPlaceholder();

        item.classList.add(this.cssClasses.dragging);
        document.body.style.userSelect = 'none';

        const rect = item.getBoundingClientRect();
        const startX = event.clientX - rect.left;
        const startY = event.clientY - rect.top;

        item.style.position = 'fixed';
        item.style.left = `${event.clientX - startX}px`;
        item.style.top = `${event.clientY - startY}px`;
        item.style.zIndex = '1000';
        item.style.width = `${rect.width}px`;
        item.style.pointerEvents = 'none';
        item.style.transform = 'rotate(5deg) scale(1.05)';

        this.dragState.offsetX = startX;
        this.dragState.offsetY = startY;

        this.showDragFeedback();
    }

    handleDrag(event) {
        if (!this.dragState.draggedItem) return;

        this.dragState.draggedItem.style.left = `${event.clientX - this.dragState.offsetX}px`;
        this.dragState.draggedItem.style.top = `${event.clientY - this.dragState.offsetY}px`;

        const elementBelow = document.elementFromPoint(event.clientX, event.clientY);
        const targetItem = elementBelow ? elementBelow.closest(this.selectors.item) : null;

        if (targetItem && targetItem !== this.dragState.draggedItem) {
            this.updatePlaceholderPosition(targetItem);
        }
    }

    endDrag(event) {
        if (!this.dragState.draggedItem) return;

        const draggedItem = this.dragState.draggedItem;
        draggedItem.classList.remove(this.cssClasses.dragging);
        draggedItem.style.position = '';
        draggedItem.style.left = '';
        draggedItem.style.top = '';
        draggedItem.style.zIndex = '';
        draggedItem.style.width = '';
        draggedItem.style.pointerEvents = '';
        draggedItem.style.transform = '';
        document.body.style.userSelect = '';

        const newIndex = this.getPlaceholderIndex();
        const oldIndex = this.dragState.draggedIndex;

        if (this.dragState.placeholder && newIndex !== -1 && newIndex !== oldIndex) {
            this.dragState.placeholder.parentNode.insertBefore(draggedItem, this.dragState.placeholder);
            void this.saveNewOrder();
        } else {
            this.dragState.draggedItem.parentNode.insertBefore(draggedItem, this.dragState.items[oldIndex].nextSibling);
        }

        this.cleanupDrag();
        this.hideDragFeedback();
        this.resetDragState();
    }

    createPlaceholder() {
        if (!this.dragState.draggedItem) return;

        this.dragState.placeholder = document.createElement('div');
        this.dragState.placeholder.className = `col-12 col-sm-6 col-lg-4 col-xl-3 ${this.cssClasses.placeholder}`;
        this.dragState.placeholder.innerHTML = `
            <div class="placeholder-content">
                <div class="placeholder-icon"><i class="fas fa-plus"></i></div>
                <span>Drop here</span>
            </div>`;

        this.dragState.draggedItem.parentNode.insertBefore(
            this.dragState.placeholder,
            this.dragState.draggedItem.nextSibling
        );
    }

    updatePlaceholderPosition(targetItem) {
        if (!this.dragState.placeholder || !targetItem) return;

        const targetIndex = this.dragState.items.indexOf(targetItem);
        const draggedIndex = this.dragState.draggedIndex;

        if (targetIndex < draggedIndex) {
            targetItem.parentNode.insertBefore(this.dragState.placeholder, targetItem);
        } else {
            targetItem.parentNode.insertBefore(this.dragState.placeholder, targetItem.nextSibling);
        }
    }

    getPlaceholderIndex() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid || !this.dragState.placeholder) return -1;
        return Array.from(grid.children).indexOf(this.dragState.placeholder);
    }

    async saveNewOrder() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return;

        const collectionId = grid.dataset.collectionId;
        const url = this.reorderUrl.replace('{id}', collectionId);
        const items = Array.from(grid.querySelectorAll(this.selectors.item));

        const payload = {
            items: items.map((item, index) => ({
                item_id: parseInt(item.dataset.itemId),
                position: index + 1
            }))
        };

        try {
            const response = await this.httpClient.sendJSON(url, payload);
            await this.httpClient.handleResponse(response, grid, {
                onSuccess: (data) => this.handleReorderSuccess(data, items),
                onError: (error) => this.handleReorderError(error),
                onLoginRedirect: () => this.handleLogoutDetection(),
            });
        } catch (error) {
            this.handleReorderError(error);
        }
    }

    handleReorderSuccess(data, items) {
        items.forEach((item, index) => {
            item.dataset.position = index + 1;
        });

        MessageManager.showGlobalMessage(
            data.message || 'Items reordered successfully!',
            'success',
            {timeout: 3000}
        );
    }

    handleReorderError(error) {
        MessageManager.showGlobalMessage(
            'Failed to reorder items. Page will refresh to restore order.',
            'error',
            {timeout: 5000}
        );
        setTimeout(() => window.location.reload(), 5000);
    }

    handleLogoutDetection() {
        const grid = document.querySelector(this.selectors.grid);

        const slug = grid.dataset.collectionSlug;
        const username = grid.dataset.collectionUsername;
        const nextPath = `/favorites/collections/${username}/${slug}/`;
        const loginUrl = `/accounts/login/?next=${encodeURIComponent(nextPath)}`;

        AuthenticationHandler.handleGlobalLogout(this.authBroadcastManager, {
            redirectUrl: loginUrl,
            message: 'Session expired. Please log in to reorder items.'
        });
    }

    cleanupDrag() {
        if (this.dragState.placeholder) {
            this.dragState.placeholder.remove();
        }
        document.querySelectorAll(`.${this.cssClasses.dragOver}`).forEach(el => {
            el.classList.remove(this.cssClasses.dragOver);
        });
    }

    showDragFeedback() {
        const grid = document.querySelector(this.selectors.grid);
        if (grid) {
            grid.classList.add('reordering');
        }
        MessageManager.showGlobalMessage(
            'Drag item to a new position and release',
            'info',
            {timeout: 3000}
        );
    }

    hideDragFeedback() {
        const grid = document.querySelector(this.selectors.grid);
        if (grid) {
            grid.classList.remove('reordering');
        }
    }

    resetDragState() {
        this.dragState = {
            draggedItem: null,
            draggedIndex: -1,
            placeholder: null,
            items: []
        };
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CollectionReorderHandler();
});
