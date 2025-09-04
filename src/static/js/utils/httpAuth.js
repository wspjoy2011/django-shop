export function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export function urlLooksLikeLogin(url) {
    if (!url) return false;
    const lower = url.toLowerCase();
    return lower.includes('/login') || lower.includes('accounts/login');
}

export function isLoginRedirectResponse(response) {
    if (response.status === 401 || response.status === 403) return true;

    if (response.redirected && response.url && urlLooksLikeLogin(response.url)) return true;

    return !!((response.status === 404 || response.status === 302) && urlLooksLikeLogin(response.url));
}

export function isLoginRedirectErrorLike(error) {
    const msg = String(error?.message || '').toLowerCase();
    return msg.includes('login') ||
        msg.includes('accounts/login') ||
        msg.includes('401') ||
        msg.includes('403') ||
        msg.includes('unauthorized') ||
        msg.includes('forbidden');
}
