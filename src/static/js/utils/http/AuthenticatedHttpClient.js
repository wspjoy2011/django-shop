import { getCookie, isLoginRedirectResponse } from '../httpAuth.js';

export class AuthenticatedHttpClient {
    constructor(csrfToken = null) {
        this.csrfToken = csrfToken || getCookie('csrftoken');
    }

    async sendRequest(url, options = {}) {
        const defaultOptions = {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            }
        };

        const mergedHeaders = {
            ...defaultOptions.headers,
            ...(options.headers || {})
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: mergedHeaders
        };

        return fetch(url, finalOptions);
    }

    async sendJSON(url, data, method = 'POST') {
        return this.sendRequest(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    }

    async sendDelete(url) {
        return this.sendRequest(url, {
            method: 'DELETE'
        });
    }

    async handleResponse(response, component, options = {}) {
        const {
            onLoginRedirect = null,
            onSuccess = null,
            onError = null
        } = options;

        if (isLoginRedirectResponse(response)) {
            if (onLoginRedirect) {
                onLoginRedirect(response.url || '/login/');
            }
            return {isLoginRedirect: true, url: response.url || '/login/'};
        }

        let data = null;
        try {
            data = await response.json();
        } catch (e) {
        }

        if (response.ok) {
            if (onSuccess) onSuccess(data);
            return {success: true, data};
        } else {
            if (data && data.error) {
                const error = new Error(data.error);
                if (onError) onError(error);
                return {success: false, error, data};
            } else if (data && onSuccess) {
                onSuccess(data);
                return {success: false, data};
            } else {
                const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                if (onError) onError(error);
                return {success: false, error};
            }
        }
    }
}
