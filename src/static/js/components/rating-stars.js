import { getCookie, isLoginRedirectResponse, isLoginRedirectErrorLike } from '../utils/httpAuth.js';
import { BroadcastManager, ComponentFinder } from '../utils/broadcastManager.js';

class RatingStarsHandler {
    constructor() {
        this.selectors = {
            component: '.rating-component',
            starsInput: '.rating-star-input',
            aggregate: '.rating-aggregate',
            value: '.rating-value',
            reviews: '.reviews-count',
            clearBtn: '.rating-clear-hover',
            messages: '.rating-messages-container',
            overlay: '.rating-interactive-overlay',
            userIndicator: '.user-rating-indicator',
            starsContainer: '.rating-stars-container',
            userRatingBadge: '.user-rating-badge-container'
        };
        this.init();
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
        this.broadcastManager = BroadcastManager.createManager('rating-updates');

        this.broadcastManager.subscribe('rating_updated', (data) => {
            this.handleRatingUpdateMessage(data);
        });

        this.broadcastManager.subscribe('rating_removed', (data) => {
            this.handleRatingRemoveMessage(data);
        });

        this.broadcastManager.subscribe('logout_detected', (data) => {
            this.handleLogoutMessage(data);
        });
    }

    handleRatingUpdateMessage(data) {
        const { productId, ratingUrl, userScore, serverStats } = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId, ratingUrl);

        componentsToUpdate.forEach(comp => {
            this.applyServerStats(comp, serverStats);
            this.toggleRatedState(comp, true);
            comp.dataset.userScore = userScore;
            this.setInitialUserRatingPreview(comp, userScore);
            this.toggleUserIndicator(comp, true, userScore);
            this.toggleUserRatingBadge(comp, true, userScore);
            this.updateContainerTitle(comp);
        });
    }

    handleRatingRemoveMessage(data) {
        const { productId, ratingUrl, serverStats } = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId, ratingUrl);

        componentsToUpdate.forEach(comp => {
            this.applyServerStats(comp, serverStats);
            this.toggleRatedState(comp, false);
            this.resetUserRatingUI(comp);
        });
    }

    handleLogoutMessage(data) {
        const { productId, ratingUrl } = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId, ratingUrl);

        componentsToUpdate.forEach(comp => {
            comp.dataset.authenticated = 'false';
            comp.dataset.userRated = 'false';
            comp.classList.remove('rated-active');
            this.resetUserRatingUI(comp);
        });
    }

    findComponentsForUpdate(productId, ratingUrl) {
        if (productId && productId.trim()) {
            return ComponentFinder.findByProductId(productId, this.selectors.component);
        } else if (ratingUrl) {
            return ComponentFinder.findByUrl(ratingUrl, this.selectors.component, 'ratingUrl');
        } else {
            return [];
        }
    }

    broadcastRatingUpdate(component, userScore, serverStats) {
        this.broadcastManager.broadcast('rating_updated', {
            productId: component.dataset.productId,
            ratingUrl: component.dataset.ratingUrl,
            userScore: userScore,
            serverStats: serverStats
        });
    }

    broadcastRatingRemove(component, serverStats) {
        this.broadcastManager.broadcast('rating_removed', {
            productId: component.dataset.productId,
            ratingUrl: component.dataset.ratingUrl,
            serverStats: serverStats
        });
    }

    broadcastLogoutDetection(component) {
        this.broadcastManager.broadcast('logout_detected', {
            productId: component.dataset.productId,
            ratingUrl: component.dataset.ratingUrl
        });
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            const star = e.target.closest(this.selectors.starsInput);
            if (star) {
                const component = star.closest(this.selectors.component);
                if (!component) return;
                e.preventDefault();
                void this.onStarClick(component, star);
                return;
            }

            const clearBtn = e.target.closest(this.selectors.clearBtn);
            if (clearBtn) {
                const component = clearBtn.closest(this.selectors.component);
                if (!component) return;
                e.preventDefault();
                void this.onClearClick(component);
            }
        });

        document.addEventListener('mouseover', (e) => {
            const star = e.target.closest(this.selectors.starsInput);
            if (star) {
                const component = star.closest(this.selectors.component);
                if (!component || !this.isAuthenticated(component)) return;
                this.previewStars(component, Number(star.dataset.score || 0));
            }
        });

        document.addEventListener('mouseout', (e) => {
            const star = e.target.closest(this.selectors.starsInput);
            if (star) {
                const component = star.closest(this.selectors.component);
                if (!component) return;
                this.previewStars(component, 0);
            }
        });

        window.addEventListener('beforeunload', () => {
            this.broadcastManager?.close();
        });
    }

    bootstrapInitialState() {
        document.querySelectorAll(this.selectors.component).forEach((comp) => {
            const userRated = comp.dataset.userRated === 'true';
            this.toggleRatedState(comp, userRated);
            if (userRated && this.isAuthenticated(comp)) {
                const userScore = Number(comp.dataset.userScore || 0);
                this.setInitialUserRatingPreview(comp, userScore);
            }
        });
    }

    setInitialUserRatingPreview(component, userScore) {
        component.querySelectorAll(this.selectors.starsInput).forEach((star) => {
            const starScore = Number(star.dataset.score || 0);
            if (starScore <= userScore) {
                star.classList.add('user-rated-star');
            }
        });
    }

    async onStarClick(component, starEl) {
        if (!this.isAuthenticated(component)) {
            this.showMessage('Login required', 'info', component);
            return;
        }
        const score = Number(starEl.dataset.score || 0);
        if (!score) return;

        const url = component.dataset.ratingUrl;
        try {
            const resp = await this.sendForm(url, {score});

            if (isLoginRedirectResponse(resp)) {
                this.handleLogoutDetection(component, resp.url);
                return;
            }

            if (!resp.ok) {
                let errorMessage = 'Failed to save rating';
                try {
                    const text = await resp.text();
                    if (text && text.trim()) {
                        errorMessage = `Server error: ${resp.status}`;
                    }
                } catch (_) {
                    this.showError('Cannot read server response', component);
                    return;
                }
                throw new Error(`${errorMessage} (${resp.status})`);
            }
            const data = await resp.json();

            const componentsToUpdate = this.getAllProductComponents(component);

            componentsToUpdate.forEach(comp => {
                this.applyServerStats(comp, data);
                this.toggleRatedState(comp, true);
                comp.dataset.userScore = score;
                this.setInitialUserRatingPreview(comp, score);
                this.toggleUserIndicator(comp, true, score);
                this.toggleUserRatingBadge(comp, true, score);
                this.updateContainerTitle(comp);
            });

            this.broadcastRatingUpdate(component, score, data);

            this.showMessage(`Rated ${score} star${score !== 1 ? 's' : ''}`, 'success', component);
        } catch (err) {
            if (isLoginRedirectErrorLike(err)) {
                this.handleLogoutDetection(component);
            } else {
                this.showError(err.message || 'Failed to save rating', component);
            }
        }
    }

    async onClearClick(component) {
        if (!this.isAuthenticated(component)) {
            this.showMessage('Login required', 'info', component);
            return;
        }
        const url = component.dataset.ratingDeleteUrl;
        try {
            const resp = await this.sendForm(url, {});

            if (isLoginRedirectResponse(resp)) {
                this.handleLogoutDetection(component, resp.url);
                return;
            }

            if (resp.status === 404) {
                const componentsToUpdate = this.getAllProductComponents(component);
                componentsToUpdate.forEach(comp => {
                    this.toggleRatedState(comp, false);
                    this.resetUserRatingUI(comp);
                });
                this.broadcastRatingRemove(component, { avg_rating: 0.0, ratings_count: 0 });
                this.showMessage('Rating was already removed', 'info', component);
                return;
            }

            if (!resp.ok) {
                let errorMessage = 'Failed to remove rating';
                try {
                    const text = await resp.text();
                    if (text && text.trim()) {
                        errorMessage = `Server error: ${resp.status}`;
                    }
                } catch (_) {
                    this.showError('Cannot read server response', component);
                    return;
                }
                throw new Error(`${errorMessage} (${resp.status})`);
            }

            const data = await resp.json();
            const componentsToUpdate = this.getAllProductComponents(component);

            componentsToUpdate.forEach(comp => {
                this.applyServerStats(comp, data);
                this.toggleRatedState(comp, false);
                this.resetUserRatingUI(comp);
            });

            this.broadcastRatingRemove(component, data);

            this.showMessage('Rating removed', 'success', component);
        } catch (err) {
            if (isLoginRedirectErrorLike(err)) {
                this.handleLogoutDetection(component);
            } else {
                this.showError(err.message || 'Failed to remove rating', component);
            }
        }
    }

    getAllProductComponents(sourceComponent) {
        const productId = sourceComponent.dataset.productId;
        const ratingUrl = sourceComponent.dataset.ratingUrl;

        if (productId && productId.trim()) {
            return ComponentFinder.findByProductId(productId, this.selectors.component);
        } else if (ratingUrl) {
            return ComponentFinder.findByUrl(ratingUrl, this.selectors.component, 'ratingUrl');
        } else {
            return [sourceComponent];
        }
    }

    handleLogoutDetection(component, loginUrl = null) {
        const componentsToUpdate = this.getAllProductComponents(component);

        componentsToUpdate.forEach(comp => {
            comp.dataset.authenticated = 'false';
            comp.dataset.userRated = 'false';
            comp.classList.remove('rated-active');
            this.resetUserRatingUI(comp);
        });

        this.broadcastLogoutDetection(component);

        const message = loginUrl ? 'Session expired.' : 'Session expired.';
        this.showMessage(message, 'warning', component);
    }

    updateContainerTitle(component) {
        const starsContainer = component.querySelector(this.selectors.starsContainer);
        if (!starsContainer) return;

        const isAuthenticated = this.isAuthenticated(component);
        const userRated = component.dataset.userRated === 'true';
        const userScore = component.dataset.userScore;

        let title;
        if (!isAuthenticated) {
            title = 'Login to rate products';
        } else if (userRated && userScore) {
            title = `Your rating: ${userScore}/5`;
        } else {
            title = 'Click to rate';
        }

        starsContainer.setAttribute('title', title);
    }

    previewStars(component, count) {
        component.querySelectorAll(this.selectors.starsInput).forEach((star) => {
            const starScore = Number(star.dataset.score || 0);
            star.classList.remove('active', 'user-rated-star');

            if (count > 0) {
                star.classList.toggle('active', starScore <= count);
            } else {
                const userScore = Number(component.dataset.userScore || 0);
                if (userScore > 0 && starScore <= userScore) {
                    star.classList.add('user-rated-star');
                }
            }
        });
    }

    toggleRatedState(component, rated) {
        component.dataset.userRated = rated ? 'true' : 'false';
        component.classList.toggle('rated-active', !!rated);
    }

    toggleUserIndicator(component, show, userScore = 0) {
        const aggregateContainer = component.querySelector(this.selectors.aggregate);
        if (!aggregateContainer) return;

        let indicator = aggregateContainer.querySelector(this.selectors.userIndicator);

        if (show && this.isAuthenticated(component)) {
            if (!indicator) {
                indicator = this.createUserIndicator(userScore);
                aggregateContainer.appendChild(indicator);
            } else {
                indicator.setAttribute('title', `Your rating: ${userScore}/5`);
            }
        } else {
            if (indicator) {
                indicator.remove();
            }
        }
    }

    toggleUserRatingBadge(component, show, userScore = 0) {
        const ratingInfo = component.querySelector('.rating-info');
        if (!ratingInfo) return;

        let badgeContainer = ratingInfo.querySelector(this.selectors.userRatingBadge);

        if (show && this.isAuthenticated(component)) {
            if (!badgeContainer) {
                badgeContainer = this.createUserRatingBadgeContainer(userScore);
                ratingInfo.appendChild(badgeContainer);
            } else {
                this.updateUserRatingBadgeContainer(badgeContainer, userScore);
            }
        } else {
            if (badgeContainer) {
                badgeContainer.remove();
            }
        }
    }

    createUserIndicator(userScore) {
        const indicator = document.createElement('span');
        indicator.className = 'user-rating-indicator';
        indicator.setAttribute('title', `Your rating: ${userScore}/5`);

        const icon = document.createElement('i');
        icon.className = 'fas fa-user-check';

        indicator.appendChild(icon);
        return indicator;
    }

    createUserRatingBadgeContainer(userScore) {
        const container = document.createElement('div');
        container.className = 'user-rating-badge-container mt-1';

        const badge = document.createElement('span');
        badge.className = 'badge bg-primary user-rating-badge';
        badge.textContent = `You: ${userScore}/5`;

        container.appendChild(badge);
        return container;
    }

    updateUserRatingBadgeContainer(container, userScore) {
        const badge = container.querySelector('.user-rating-badge');
        if (badge) {
            badge.textContent = `You: ${userScore}/5`;
        }
    }

    resetUserRatingUI(component) {
        component.dataset.userScore = '';
        component.querySelectorAll(this.selectors.starsInput).forEach((star) => {
            star.classList.remove('user-rated-star');
        });
        this.toggleUserIndicator(component, false, 0);
        this.toggleUserRatingBadge(component, false, 0);
        this.updateContainerTitle(component);
    }

    applyServerStats(component, data) {
        const valueEl = component.querySelector(this.selectors.value);
        if (valueEl && typeof data.avg_rating !== 'undefined') {
            valueEl.textContent = Number(data.avg_rating).toFixed(1);
        }
        const reviewsEl = component.querySelector(this.selectors.reviews);
        if (reviewsEl && typeof data.ratings_count !== 'undefined') {
            const n = Number(data.ratings_count) || 0;
            reviewsEl.textContent = n > 0 ? `(${n} review${n === 1 ? '' : 's'})` : '';
        }
    }

    async sendForm(url, obj) {
        const body = new URLSearchParams();
        for (const [k, v] of Object.entries(obj)) {
            body.append(k, String(v));
        }
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            },
            body: body.toString()
        });
    }

    isAuthenticated(component) {
        return component.dataset.authenticated === 'true';
    }

    showError(message, component) {
        this.showMessage(message, 'error', component);
    }

    showMessage(message, type, component) {
        const container = component.querySelector(this.selectors.messages);
        if (!container) {
            return;
        }

        container.innerHTML = '';
        const el = this.createMessageElement(message, type);
        container.appendChild(el);
        setTimeout(() => this.removeMessage(el), type === 'error' ? 3000 : 2000);
        el.addEventListener('click', () => this.removeMessage(el));
    }

    createMessageElement(message, type) {
        const wrap = document.createElement('div');
        const cls = {
            success: 'bg-success',
            error: 'bg-danger',
            info: 'bg-info',
            warning: 'bg-warning',
        }[type] || 'bg-info';
        wrap.className = `${cls}`;
        wrap.textContent = message;
        wrap.style.cursor = 'pointer';
        wrap.style.userSelect = 'none';
        wrap.style.animation = 'fadeInUp .2s ease-out';
        return wrap;
    }

    removeMessage(el) {
        if (!el || !el.parentNode) return;
        el.style.animation = 'fadeOutUp .2s ease-in';
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 200);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new RatingStarsHandler();
});
