import {ComponentFinder} from '../utils/broadcastManager.js';
import {BaseComponent} from '../utils/components/BaseComponent.js';
import {MessageManager} from '../utils/components/MessageManager.js';
import {AuthenticationHandler} from '../utils/components/AuthenticationHandler.js';
import {AuthenticatedHttpClient} from '../utils/http/AuthenticatedHttpClient.js';

class RatingStarsHandler extends BaseComponent {
    constructor() {
        super({broadcastChannelName: 'rating-updates'});

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

        this.httpClient = new AuthenticatedHttpClient();
        this.init();
    }

    setupBroadcastSubscriptions() {
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
        const {productId, ratingUrl, userScore, serverStats} = data;
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
        const {productId, ratingUrl, serverStats} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId, ratingUrl);

        componentsToUpdate.forEach(comp => {
            this.applyServerStats(comp, serverStats);
            this.toggleRatedState(comp, false);
            this.resetUserRatingUI(comp);
        });
    }

    handleLogoutMessage(data) {
        const {productId, ratingUrl} = data;
        const componentsToUpdate = this.findComponentsForUpdate(productId, ratingUrl);

        componentsToUpdate.forEach(comp => {
            AuthenticationHandler.resetAuthenticationState(comp, (component) => {
                component.dataset.userRated = 'false';
                component.classList.remove('rated-active');
                this.resetUserRatingUI(component);
            });
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

    bindEvents() {
        super.bindEvents();

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
            MessageManager.showMessage('Login required', 'info', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
            return;
        }

        const score = Number(starEl.dataset.score || 0);
        if (!score) return;

        const url = component.dataset.ratingUrl;
        try {
            const result = await this.httpClient.handleResponse(
                await this.httpClient.sendJSON(url, {score}),
                component,
                {
                    onLoginRedirect: (loginUrl) => this.handleLogoutDetection(component, loginUrl),
                    onSuccess: (data) => {
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
                        MessageManager.showMessage(`Rated ${score} star${score !== 1 ? 's' : ''}`, 'success', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
                    },
                    onError: (error) => {
                        let errorMessage = 'Failed to save rating';
                        if (error.message.includes('Cannot read server response')) {
                            errorMessage = 'Cannot read server response';
                        } else if (error.message.includes('Server error')) {
                            errorMessage = `Server error: ${error.message.split(': ')[1]}`;
                        }
                        MessageManager.showMessage(errorMessage, 'error', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
                    }
                }
            );

        } catch (err) {
            if (AuthenticationHandler.isAuthenticationError(err)) {
                this.handleLogoutDetection(component);
            } else {
                MessageManager.showMessage(err.message || 'Failed to save rating', 'error', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
            }
        }
    }

    async onClearClick(component) {
        if (!this.isAuthenticated(component)) {
            MessageManager.showMessage('Login required', 'info', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
            return;
        }

        const url = component.dataset.ratingDeleteUrl;
        try {
            const response = await this.httpClient.sendDelete(url);

            if (AuthenticationHandler.isLoginRedirect(response)) {
                this.handleLogoutDetection(component, response.url);
                return;
            }

            if (response.status === 404) {
                const componentsToUpdate = this.getAllProductComponents(component);
                componentsToUpdate.forEach(comp => {
                    this.toggleRatedState(comp, false);
                    this.resetUserRatingUI(comp);
                });
                this.broadcastRatingRemove(component, {avg_rating: 0.0, ratings_count: 0});
                MessageManager.showMessage('Rating was already removed', 'info', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
                return;
            }

            const result = await this.httpClient.handleResponse(response, component, {
                onSuccess: (data) => {
                    const componentsToUpdate = this.getAllProductComponents(component);
                    componentsToUpdate.forEach(comp => {
                        this.applyServerStats(comp, data);
                        this.toggleRatedState(comp, false);
                        this.resetUserRatingUI(comp);
                    });

                    this.broadcastRatingRemove(component, data);
                    MessageManager.showMessage('Rating removed', 'success', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
                }
            });

        } catch (err) {
            if (AuthenticationHandler.isAuthenticationError(err)) {
                this.handleLogoutDetection(component);
            } else {
                MessageManager.showMessage(err.message || 'Failed to remove rating', 'error', component.querySelector(this.selectors.messages), MessageManager.RATING_CONFIG);
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
        AuthenticationHandler.handleLogoutDetection(component, this.broadcastManager, {
            loginUrl,
            messageManager: MessageManager,
            messageContainer: component.querySelector(this.selectors.messages),
            productIdGetter: (comp, forBroadcast = false) => {
                if (forBroadcast) {
                    return {
                        productId: comp.dataset.productId,
                        ratingUrl: comp.dataset.ratingUrl
                    };
                }
                return this.getAllProductComponents(comp);
            },
            resetCallback: (comp) => {
                comp.dataset.userRated = 'false';
                comp.classList.remove('rated-active');
                this.resetUserRatingUI(comp);
            }
        });
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
}

document.addEventListener('DOMContentLoaded', () => {
    new RatingStarsHandler();
});
