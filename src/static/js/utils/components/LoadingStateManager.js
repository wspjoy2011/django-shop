export class LoadingStateManager {
    static setLoadingState(component, isLoading, options = {}) {
        const {
            selectors = {},
            cssClasses = {},
            disablePointerEvents = false
        } = options;

        const buttonSelectors = [
            selectors.button,
            selectors.submitButton,
            selectors.buttons
        ].filter(Boolean);

        buttonSelectors.forEach(selector => {
            const buttons = Array.isArray(selector) ? selector :
                (typeof selector === 'string' ? component.querySelectorAll(selector) : [selector]);

            buttons.forEach(button => {
                if (!button) return;

                if (isLoading) {
                    if (cssClasses.disabled) {
                        button.classList.add(cssClasses.disabled);
                    }
                    button.disabled = true;
                    if (disablePointerEvents) {
                        button.style.pointerEvents = 'none';
                    }
                } else {
                    if (cssClasses.disabled) {
                        button.classList.remove(cssClasses.disabled);
                    }
                    button.disabled = false;
                    if (disablePointerEvents) {
                        button.style.pointerEvents = '';
                    }
                }
            });
        });

        if (selectors.loadingSpinner) {
            const spinner = component.querySelector(selectors.loadingSpinner);
            if (spinner && cssClasses.hidden) {
                spinner.classList.toggle(cssClasses.hidden, !isLoading);
            }
        }
    }

    static isLoading(component, options = {}) {
        const { selector = null, cssClass = 'disabled' } = options;

        if (selector) {
            const button = component.querySelector(selector);
            return button && button.classList.contains(cssClass);
        }

        return component.querySelector(`.${cssClass}`) !== null;
    }

    static setModalLoadingState(modal, isLoading, selectors = {}, cssClasses = {}) {
        if (!modal) return;

        const submitButton = modal.querySelector(selectors.submitButton);
        const spinner = modal.querySelector(selectors.loadingSpinner);

        if (submitButton) {
            submitButton.disabled = isLoading;
        }

        if (spinner && cssClasses.hidden) {
            spinner.classList.toggle(cssClasses.hidden, !isLoading);
        }
    }
}
