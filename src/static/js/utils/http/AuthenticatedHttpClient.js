import {getCookie, isLoginRedirectResponse} from '../httpAuth.js';

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

    async sendForm(url, data) {
        const body = new URLSearchParams();
        for (const [k, v] of Object.entries(data)) {
            body.append(k, String(v));
        }

        return this.sendRequest(url, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
            },
            body: body.toString()
        });
    }

    async sendJSON(url, data) {
        return this.sendRequest(url, {
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    }

    async handleResponse(response, component, options = {}) {
        const {
            onLoginRedirect = null,
            onSuccess = null,
            onError = null
        } = options;

        if (isLoginRedirectResponse(response)) {
            if (onLoginRedirect) onLoginRedirect(response.url);
            return {isLoginRedirect: true, url: response.url};
        }

        const data = await response.json().catch(() => null);

        if (response.ok) {
            if (onSuccess) onSuccess(data);
            return {success: true, data};
        } else {
            if (data && onSuccess) {
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
