import {getCookie} from '../httpAuth.js';
import {BroadcastManager} from '../broadcastManager.js';

export class BaseComponent {
    constructor(options = {}) {
        this.selectors = {};
        this.cssClasses = {};
        this.broadcastManager = null;
        this.authBroadcastManager = null;
        this.csrfToken = null;
        this.broadcastChannelName = options.broadcastChannelName;

        this.bindEvents = this.bindEvents.bind(this);
        this.setupBroadcastChannel = this.setupBroadcastChannel.bind(this);
        this.bootstrapInitialState = this.bootstrapInitialState.bind(this);
    }

    init() {
        this.setupCSRF();
        this.setupBroadcastChannel();
        this.setupAuthBroadcastChannel();
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

    setupAuthBroadcastChannel() {
        this.authBroadcastManager = BroadcastManager.createManager('auth-updates');
        this.setupAuthBroadcastSubscriptions();
    }

    setupBroadcastSubscriptions() {
    }

    setupAuthBroadcastSubscriptions() {
    }

    bindEvents() {
        window.addEventListener('beforeunload', () => {
            this.broadcastManager?.close();
            this.authBroadcastManager?.close();
        });
    }

    bootstrapInitialState() {
    }

    isAuthenticated(component) {
        return component.dataset.authenticated === 'true';
    }

    destroy() {
        this.broadcastManager?.close();
        this.authBroadcastManager?.close();
    }
}
