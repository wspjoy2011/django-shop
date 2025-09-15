import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';

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

        this.dragState = {
            draggedItem: null,
            draggedIndex: -1,
            placeholder: null,
            items: []
        };

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
            const handle = e.target.closest(this.selectors.dragHandle);
            if (handle) {
                const item = handle.closest(this.selectors.item);
                if (item) {
                    e.preventDefault();
                    this.startDrag(item, e);
                }
            }
        });

        document.addEventListener('touchstart', (e) => {
            const handle = e.target.closest(this.selectors.dragHandle);
            if (handle) {
                const item = handle.closest(this.selectors.item);
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
        const grid = document.querySelector(this.selectors.grid);

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

        if (this.dragState.placeholder && newIndex !== oldIndex) {
            this.dragState.placeholder.parentNode.insertBefore(draggedItem, this.dragState.placeholder);

            this.saveNewOrder();
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
                <div class="placeholder-icon">
                    <i class="fas fa-plus"></i>
                </div>
                <span>Drop here</span>
            </div>
        `;

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

        const allChildren = Array.from(grid.children);
        return allChildren.indexOf(this.dragState.placeholder);
    }

    saveNewOrder() {
        const grid = document.querySelector(this.selectors.grid);
        if (!grid) return;

        const items = Array.from(grid.querySelectorAll(this.selectors.item));
        const newOrder = items.map((item, index) => ({
            id: item.dataset.itemId,
            position: index + 1
        }));

        console.log('New order:', newOrder);

        MessageManager.showGlobalMessage(
            'Items reordered successfully!',
            'success',
            {timeout: 2000}
        );

        items.forEach((item, index) => {
            item.dataset.position = index + 1;
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
            'Drag the item to a new position and release to reorder',
            'info',
            {timeout: 2000}
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
