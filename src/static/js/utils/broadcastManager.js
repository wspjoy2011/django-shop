export class BroadcastManager {
    constructor(channelName) {
        this.channelName = channelName;
        this.channel = null;
        this.listeners = new Map();
        this.init();
    }

    init() {
        if (typeof BroadcastChannel !== 'undefined') {
            this.channel = new BroadcastChannel(this.channelName);
            this.channel.addEventListener('message', (event) => {
                this.handleMessage(event.data);
            });
        }
    }

    subscribe(messageType, callback) {
        if (!this.listeners.has(messageType)) {
            this.listeners.set(messageType, new Set());
        }
        this.listeners.get(messageType).add(callback);
    }

    unsubscribe(messageType, callback) {
        const callbacks = this.listeners.get(messageType);
        if (callbacks) {
            callbacks.delete(callback);
            if (callbacks.size === 0) {
                this.listeners.delete(messageType);
            }
        }
    }

    broadcast(messageType, data = {}) {
        if (!this.channel) return;

        const message = {
            type: messageType,
            timestamp: Date.now(),
            ...data
        };

        this.channel.postMessage(message);
    }

    handleMessage(data) {
        if (!data || !data.type) return;

        const callbacks = this.listeners.get(data.type);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Broadcast callback error for ${data.type}:`, error);
                }
            });
        }
    }

    close() {
        if (this.channel) {
            this.channel.close();
            this.channel = null;
        }
        this.listeners.clear();
    }

    static createManager(channelName) {
        return new BroadcastManager(channelName);
    }
}

export class ComponentFinder {
    static findByProductId(productId, selector) {
        if (!productId || !productId.trim()) return [];

        return Array.from(document.querySelectorAll(selector))
            .filter(element => element.dataset.productId === productId);
    }

    static findByUrl(url, selector, urlAttribute) {
        if (!url) return [];

        return Array.from(document.querySelectorAll(selector))
            .filter(element => element.dataset[urlAttribute] === url);
    }

    static findByCollectionId(collectionId, selector) {
        if (!collectionId) return [];

        return Array.from(document.querySelectorAll(selector))
            .filter(element => element.getAttribute('data-collection-id') === String(collectionId));
    }
}
