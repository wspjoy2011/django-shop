import {getCookie} from '../httpAuth.js';
import {BroadcastManager} from '../broadcastManager.js';

export class BaseComponent {
    constructor(options = {}) {
        this.selectors = {};
        this.cssClasses = {};
        this.broadcastManager = null;
        this.csrfToken = null;
        this.broadcastChannelName = options.broadcastChannelName;

        this.bindEvents = this.bindEvents.bind(this);
        this.setupBroadcastChannel = this.setupBroadcastChannel.bind(this);
        this.bootstrapInitialState = this.bootstrapInitialState.bind(this);
    }

    init() {
        this.setupCSRF();
        this.setupBroadcastChannel();
        this.bindEvents();
        this.bootstrapInitialState();
    }

    setupCSRF() {
        this.csrfToken = getCookie('csrftoken');
    }

    setupBroadcastChannel() {
        if (this.broadcastChannelName) {
            this.broadcastManager = BroadcastManager.createManager(this.broadcastChannelName);
            this.setupBroadcastSubscriptions();
        }
    }

    setupBroadcastSubscriptions() {
    }

    bindEvents() {
        window.addEventListener('beforeunload', () => {
            this.broadcastManager?.close();
        });
    }

    bootstrapInitialState() {
    }

    isAuthenticated(component) {
        return component.dataset.authenticated === 'true';
    }

    destroy() {
        this.broadcastManager?.close();
    }
}
