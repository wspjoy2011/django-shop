import {isLoginRedirectResponse, isLoginRedirectErrorLike} from '../httpAuth.js';
import {MessageManager} from './MessageManager.js';

let isLogoutHandled = false;

export class AuthenticationHandler {

    static validateAuthentication(component) {
        return component.dataset.authenticated === 'true';
    }

    static handleGlobalLogout(authBroadcastManager, options = {}) {
        if (isLogoutHandled) return;
        isLogoutHandled = true;

        const {redirectUrl = null, redirectTimeout = 3000} = options;

        const message = redirectUrl
            ? 'Your session has expired. You will be redirected to the login page.'
            : 'Your session has expired. Please log in again.';

        MessageManager.showGlobalMessage(message, 'warning', {timeout: redirectTimeout});

        if (authBroadcastManager) {
            authBroadcastManager.broadcast('logout_detected', {});
        }

        if (redirectUrl) {
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, redirectTimeout);
        }

        setTimeout(() => {
            isLogoutHandled = false;
        }, 500);
    }

    static resetAuthenticationState(component, resetCallback = null) {
        component.dataset.authenticated = 'false';

        if (resetCallback) {
            resetCallback(component);
        }
    }

    static applyUnauthenticatedState(component, options = {}) {
        const {cssClasses = {}, selectors = {}, resetCallback = null} = options;

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
