import { isLoginRedirectResponse, isLoginRedirectErrorLike } from '../httpAuth.js';

export class AuthenticationHandler {

    static validateAuthentication(component) {
        return component.dataset.authenticated === 'true';
    }

    static handleLogoutDetection(component, broadcastManager, options = {}) {
        const {
            loginUrl = null,
            messageManager = null,
            messageContainer = null,
            resetCallback = null,
            productIdGetter = null
        } = options;

        const componentsToUpdate = productIdGetter ?
            productIdGetter(component) : [component];

        componentsToUpdate.forEach(comp => {
            this.resetAuthenticationState(comp, resetCallback);
        });

        if (broadcastManager) {
            const broadcastData = productIdGetter ?
                productIdGetter(component, true) : {};
            broadcastManager.broadcast('logout_detected', broadcastData);
        }

        const message = loginUrl ? 'Session expired.' : 'Session expired.';
        if (messageManager && messageContainer) {
            messageManager.showMessage(message, 'warning', messageContainer);
        }
    }

    static resetAuthenticationState(component, resetCallback = null) {
        component.dataset.authenticated = 'false';

        if (resetCallback) {
            resetCallback(component);
        }
    }

    static applyUnauthenticatedState(component, options = {}) {
        const { cssClasses = {}, selectors = {}, resetCallback = null } = options;

        component.dataset.authenticated = 'false';

        if (cssClasses.unauthenticated) {
            component.classList.add(cssClasses.unauthenticated);
        }

        if (selectors.buttons) {
            const buttons = component.querySelectorAll(selectors.buttons);
            buttons.forEach(b => (b.style.cursor = 'default'));
        }

        if (resetCallback) {
            resetCallback(component);
        }
    }

    static isAuthenticationError(error) {
        return isLoginRedirectErrorLike(error);
    }

    static isLoginRedirect(response) {
        return isLoginRedirectResponse(response);
    }
}
