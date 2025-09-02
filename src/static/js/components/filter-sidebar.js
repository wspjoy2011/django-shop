class CatalogFilterSidebar {
    constructor() {
        this.selectors = {
            filterButton: '#filterButton',
            filterOverlay: '#filterOverlay',
            filterSidebar: '#filterSidebar',
            closeSidebar: '#closeSidebar',
            reset: '#resetFilters',
            apply: '#applyFilters',

            genderAll: '#gender_all',
            genderItems: '.gender-checkbox',
            genderToggle: '#genderToggleBtn',
            genderSection: '#genderSection',

            seasonAll: '#season_all',
            seasonItems: '.season-checkbox',
            seasonToggle: '#seasonToggleBtn',
            seasonSection: '#seasonSection',

            priceToggle: '#priceToggleBtn',
            priceSection: '#priceSection',
            priceRangeMin: '#priceRangeMin',
            priceRangeMax: '#priceRangeMax',
            minPriceInput: '#minPriceInput',
            maxPriceInput: '#maxPriceInput',
            currentPriceDisplay: '#currentPriceDisplay',

            availabilityAll: '#availability_all',
            availabilityItems: '.availability-checkbox',
            availabilityToggle: '#availabilityToggleBtn',
            availabilitySection: '#availabilitySection',

            discountAll: '#discount_all',
            discountItems: '.discount-checkbox',
            discountToggle: '#discountToggleBtn',
            discountSection: '#discountSection',
        };

        this.refs = {};
        this.lastChanged = 'min';
        this.init();
    }

    init() {
        this.cacheDom();
        this.bindEvents();
        this.bootstrapState();
        this.initPriceSlider();
    }

    cacheDom() {
        const q = (sel) => document.querySelector(sel);
        const qa = (sel) => document.querySelectorAll(sel);

        this.refs.filterButton = q(this.selectors.filterButton);
        this.refs.filterOverlay = q(this.selectors.filterOverlay);
        this.refs.filterSidebar = q(this.selectors.filterSidebar);
        this.refs.closeSidebar = q(this.selectors.closeSidebar);
        this.refs.reset = q(this.selectors.reset);
        this.refs.apply = q(this.selectors.apply);

        this.refs.genderAll = q(this.selectors.genderAll);
        this.refs.genderItems = qa(this.selectors.genderItems);
        this.refs.genderToggle = q(this.selectors.genderToggle);
        this.refs.genderSection = q(this.selectors.genderSection);

        this.refs.seasonAll = q(this.selectors.seasonAll);
        this.refs.seasonItems = qa(this.selectors.seasonItems);
        this.refs.seasonToggle = q(this.selectors.seasonToggle);
        this.refs.seasonSection = q(this.selectors.seasonSection);

        this.refs.priceToggle = q(this.selectors.priceToggle);
        this.refs.priceSection = q(this.selectors.priceSection);
        this.refs.priceRangeMin = q(this.selectors.priceRangeMin);
        this.refs.priceRangeMax = q(this.selectors.priceRangeMax);
        this.refs.minPriceInput = q(this.selectors.minPriceInput);
        this.refs.maxPriceInput = q(this.selectors.maxPriceInput);
        this.refs.currentPriceDisplay = q(this.selectors.currentPriceDisplay);

        this.refs.availabilityAll = q(this.selectors.availabilityAll);
        this.refs.availabilityItems = qa(this.selectors.availabilityItems);
        this.refs.availabilityToggle = q(this.selectors.availabilityToggle);
        this.refs.availabilitySection = q(this.selectors.availabilitySection);

        this.refs.discountAll = q(this.selectors.discountAll);
        this.refs.discountItems = qa(this.selectors.discountItems);
        this.refs.discountToggle = q(this.selectors.discountToggle);
        this.refs.discountSection = q(this.selectors.discountSection);
    }

    bindEvents() {
        const {
            filterButton, filterOverlay, filterSidebar, closeSidebar,
            reset, apply,
            genderAll, genderToggle,
            seasonAll, seasonToggle,
            priceToggle,
            availabilityAll, availabilityToggle,
            discountAll, discountToggle
        } = this.refs;

        if (filterButton) filterButton.addEventListener('click', () => this.openSidebar());
        if (closeSidebar) closeSidebar.addEventListener('click', () => this.closeSidebar());
        if (filterOverlay) filterOverlay.addEventListener('click', () => this.closeSidebar());

        if (reset) reset.addEventListener('click', () => this.resetFilters());
        if (apply) apply.addEventListener('click', () => this.applyFilters());

        if (genderAll) {
            genderAll.addEventListener('change', () => {
                if (genderAll.checked) {
                    this.setAll(this.refs.genderItems, false);
                    this.setCollapsed(this.refs.genderToggle, this.refs.genderSection, true);
                }
                this.updateAllState('gender');
            });
        }

        this.onEach(this.refs.genderItems, (el) => {
            el.addEventListener('change', () => {
                this.updateAllState('gender');
                if (this.anyChecked(this.refs.genderItems)) {
                    this.setCollapsed(this.refs.genderToggle, this.refs.genderSection, false);
                }
            });
        });

        if (seasonAll) {
            seasonAll.addEventListener('change', () => {
                if (seasonAll.checked) {
                    this.setAll(this.refs.seasonItems, false);
                    this.setCollapsed(this.refs.seasonToggle, this.refs.seasonSection, true);
                }
                this.updateAllState('season');
            });
        }

        this.onEach(this.refs.seasonItems, (el) => {
            el.addEventListener('change', () => {
                this.updateAllState('season');
                if (this.anyChecked(this.refs.seasonItems)) {
                    this.setCollapsed(this.refs.seasonToggle, this.refs.seasonSection, false);
                }
            });
        });

        if (availabilityAll) {
            availabilityAll.addEventListener('change', () => {
                if (availabilityAll.checked) {
                    this.setAll(this.refs.availabilityItems, false);
                    this.setCollapsed(this.refs.availabilityToggle, this.refs.availabilitySection, true);
                }
                this.updateAllState('availability');
            });
        }

        this.onEach(this.refs.availabilityItems, (el) => {
            el.addEventListener('change', () => {
                this.updateAllState('availability');
                if (this.anyChecked(this.refs.availabilityItems)) {
                    this.setCollapsed(this.refs.availabilityToggle, this.refs.availabilitySection, false);
                }
            });
        });

        if (discountAll) {
            discountAll.addEventListener('change', () => {
                if (discountAll.checked) {
                    this.setAll(this.refs.discountItems, false);
                    this.setCollapsed(this.refs.discountToggle, this.refs.discountSection, true);
                }
                this.updateAllState('discount');
            });
        }

        this.onEach(this.refs.discountItems, (el) => {
            el.addEventListener('change', () => {
                this.updateAllState('discount');
                if (this.anyChecked(this.refs.discountItems)) {
                    this.setCollapsed(this.refs.discountToggle, this.refs.discountSection, false);
                }
            });
        });

        // Toggle events
        if (genderToggle) {
            genderToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isExpanded = genderToggle.getAttribute('aria-expanded') === 'true';
                this.setCollapsed(genderToggle, this.refs.genderSection, isExpanded);
            });
        }

        if (seasonToggle) {
            seasonToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isExpanded = seasonToggle.getAttribute('aria-expanded') === 'true';
                this.setCollapsed(seasonToggle, this.refs.seasonSection, isExpanded);
            });
        }

        if (priceToggle) {
            priceToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isExpanded = priceToggle.getAttribute('aria-expanded') === 'true';
                this.setCollapsed(priceToggle, this.refs.priceSection, isExpanded);
            });
        }

        if (availabilityToggle) {
            availabilityToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isExpanded = availabilityToggle.getAttribute('aria-expanded') === 'true';
                this.setCollapsed(availabilityToggle, this.refs.availabilitySection, isExpanded);
            });
        }

        if (discountToggle) {
            discountToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const isExpanded = discountToggle.getAttribute('aria-expanded') === 'true';
                this.setCollapsed(discountToggle, this.refs.discountSection, isExpanded);
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && filterSidebar && filterSidebar.classList.contains('active')) {
                this.closeSidebar();
            }
        });
    }

    initPriceSlider() {
        const { priceRangeMin, priceRangeMax, minPriceInput, maxPriceInput, currentPriceDisplay } = this.refs;

        if (!priceRangeMin || !priceRangeMax || !minPriceInput || !maxPriceInput) return;

        const updateSliderTrack = () => {
            const min = parseFloat(priceRangeMin.min);
            const max = parseFloat(priceRangeMax.max);
            const minVal = parseFloat(priceRangeMin.value);
            const maxVal = parseFloat(priceRangeMax.value);

            const range = document.querySelector('.price-slider-range');
            if (range) {
                const left = ((minVal - min) / (max - min)) * 100;
                const width = ((maxVal - minVal) / (max - min)) * 100;

                range.style.left = left + '%';
                range.style.width = width + '%';
            }

            if (currentPriceDisplay) {
                currentPriceDisplay.textContent = `$${minVal.toFixed(2)} - $${maxVal.toFixed(2)}`;
            }
        };

        const syncInputs = () => {
            minPriceInput.value = parseFloat(priceRangeMin.value).toFixed(2);
            maxPriceInput.value = parseFloat(priceRangeMax.value).toFixed(2);
            updateSliderTrack();
        };

        const syncSliders = () => {
            let minVal = parseFloat(minPriceInput.value) || parseFloat(priceRangeMin.min);
            let maxVal = parseFloat(maxPriceInput.value) || parseFloat(priceRangeMax.max);

            if (minVal > maxVal) {
                if (this.lastChanged === 'min') {
                    maxVal = minVal;
                    maxPriceInput.value = maxVal.toFixed(2);
                } else {
                    minVal = maxVal;
                    minPriceInput.value = minVal.toFixed(2);
                }
            }

            const originalMin = parseFloat(priceRangeMin.min);
            const originalMax = parseFloat(priceRangeMax.max);

            minVal = Math.max(originalMin, Math.min(originalMax, minVal));
            maxVal = Math.max(originalMin, Math.min(originalMax, maxVal));

            priceRangeMin.value = minVal;
            priceRangeMax.value = maxVal;
            updateSliderTrack();
        };

        priceRangeMin.addEventListener('input', () => {
            if (parseFloat(priceRangeMin.value) > parseFloat(priceRangeMax.value)) {
                priceRangeMax.value = priceRangeMin.value;
            }
            syncInputs();
        });

        priceRangeMax.addEventListener('input', () => {
            if (parseFloat(priceRangeMax.value) < parseFloat(priceRangeMin.value)) {
                priceRangeMin.value = priceRangeMax.value;
            }
            syncInputs();
        });

        minPriceInput.addEventListener('input', () => {
            this.lastChanged = 'min';
            syncSliders();
        });

        maxPriceInput.addEventListener('input', () => {
            this.lastChanged = 'max';
            syncSliders();
        });

        minPriceInput.addEventListener('blur', () => {
            syncSliders();
        });

        maxPriceInput.addEventListener('blur', () => {
            syncSliders();
        });

        updateSliderTrack();
    }

    bootstrapState() {
        const genderCollapsed = !this.anyChecked(this.refs.genderItems);
        const seasonCollapsed = !this.anyChecked(this.refs.seasonItems);

        const url = new URL(window.location.href);
        const hasMinPrice = url.searchParams.has('min_price');
        const hasMaxPrice = url.searchParams.has('max_price');
        const priceCollapsed = !hasMinPrice && !hasMaxPrice;

        const availabilityCollapsed = !this.anyChecked(this.refs.availabilityItems);
        const discountCollapsed = !this.anyChecked(this.refs.discountItems);

        this.setCollapsed(this.refs.genderToggle, this.refs.genderSection, genderCollapsed);
        this.setCollapsed(this.refs.seasonToggle, this.refs.seasonSection, seasonCollapsed);
        this.setCollapsed(this.refs.priceToggle, this.refs.priceSection, priceCollapsed);
        this.setCollapsed(this.refs.availabilityToggle, this.refs.availabilitySection, availabilityCollapsed);
        this.setCollapsed(this.refs.discountToggle, this.refs.discountSection, discountCollapsed);

        this.updateAllState('gender');
        this.updateAllState('season');
        this.updateAllState('availability');
        this.updateAllState('discount');
    }

    openSidebar() {
        const {filterSidebar, filterOverlay} = this.refs;
        if (!filterSidebar || !filterOverlay) return;
        filterOverlay.classList.add('active');
        filterSidebar.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    closeSidebar() {
        const {filterSidebar, filterOverlay} = this.refs;
        if (!filterSidebar || !filterOverlay) return;
        filterOverlay.classList.remove('active');
        filterSidebar.classList.remove('active');
        document.body.style.overflow = '';
    }

    setCollapsed(toggleBtn, bodyEl, collapsed) {
        if (!toggleBtn || !bodyEl) return;
        toggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        bodyEl.classList.toggle('show', !collapsed);
    }

    anyChecked(nodeList) {
        return Array.from(nodeList || []).some((el) => el.checked);
    }

    setAll(nodeList, checked) {
        this.onEach(nodeList, (el) => {
            el.checked = checked;
        });
    }

    updateAllState(scope) {
        if (scope === 'gender') {
            const all = this.refs.genderAll;
            if (all) all.checked = !this.anyChecked(this.refs.genderItems);
            return;
        }
        if (scope === 'season') {
            const all = this.refs.seasonAll;
            if (all) all.checked = !this.anyChecked(this.refs.seasonItems);
            return;
        }
        if (scope === 'availability') {
            const all = this.refs.availabilityAll;
            if (all) all.checked = !this.anyChecked(this.refs.availabilityItems);
            return;
        }
        if (scope === 'discount') {
            const all = this.refs.discountAll;
            if (all) all.checked = !this.anyChecked(this.refs.discountItems);
        }
    }

    resetFilters() {
        if (this.refs.genderAll) this.refs.genderAll.checked = true;
        this.setAll(this.refs.genderItems, false);
        this.setCollapsed(this.refs.genderToggle, this.refs.genderSection, true);

        if (this.refs.seasonAll) this.refs.seasonAll.checked = true;
        this.setAll(this.refs.seasonItems, false);
        this.setCollapsed(this.refs.seasonToggle, this.refs.seasonSection, true);

        if (this.refs.priceRangeMin && this.refs.priceRangeMax) {
            this.refs.priceRangeMin.value = this.refs.priceRangeMin.min;
            this.refs.priceRangeMax.value = this.refs.priceRangeMax.max;
            this.refs.minPriceInput.value = parseFloat(this.refs.priceRangeMin.min).toFixed(2);
            this.refs.maxPriceInput.value = parseFloat(this.refs.priceRangeMax.max).toFixed(2);

            const range = document.querySelector('.price-slider-range');
            if (range) {
                range.style.left = '0%';
                range.style.width = '100%';
            }

            if (this.refs.currentPriceDisplay) {
                const min = parseFloat(this.refs.priceRangeMin.min);
                const max = parseFloat(this.refs.priceRangeMax.max);
                this.refs.currentPriceDisplay.textContent = `$${min.toFixed(2)} - $${max.toFixed(2)}`;
            }
        }
        this.setCollapsed(this.refs.priceToggle, this.refs.priceSection, true);

        if (this.refs.availabilityAll) this.refs.availabilityAll.checked = true;
        this.setAll(this.refs.availabilityItems, false);
        this.setCollapsed(this.refs.availabilityToggle, this.refs.availabilitySection, true);

        if (this.refs.discountAll) this.refs.discountAll.checked = true;
        this.setAll(this.refs.discountItems, false);
        this.setCollapsed(this.refs.discountToggle, this.refs.discountSection, true);

        this.updateAllState('gender');
        this.updateAllState('season');
        this.updateAllState('availability');
        this.updateAllState('discount');
    }

    applyFilters() {
        const url = new URL(window.location.href);

        const genders = Array.from(this.refs.genderItems || [])
            .filter((el) => el.checked)
            .map((el) => el.value);
        if (genders.length) url.searchParams.set('gender', genders.join(','));
        else url.searchParams.delete('gender');

        const seasons = Array.from(this.refs.seasonItems || [])
            .filter((el) => el.checked)
            .map((el) => el.value);
        if (seasons.length) url.searchParams.set('season', seasons.join(','));
        else url.searchParams.delete('season');

        if (this.refs.minPriceInput && this.refs.maxPriceInput) {
            const minPrice = parseFloat(this.refs.minPriceInput.value);
            const maxPrice = parseFloat(this.refs.maxPriceInput.value);
            const originalMin = parseFloat(this.refs.priceRangeMin.min);
            const originalMax = parseFloat(this.refs.priceRangeMax.max);

            if (minPrice > originalMin) {
                url.searchParams.set('min_price', minPrice.toFixed(2));
            } else {
                url.searchParams.delete('min_price');
            }

            if (maxPrice < originalMax) {
                url.searchParams.set('max_price', maxPrice.toFixed(2));
            } else {
                url.searchParams.delete('max_price');
            }
        }

        const availability = Array.from(this.refs.availabilityItems || [])
            .filter((el) => el.checked)
            .map((el) => el.value);
        if (availability.length) url.searchParams.set('availability', availability.join(','));
        else url.searchParams.delete('availability');

        const discount = Array.from(this.refs.discountItems || [])
            .filter((el) => el.checked)
            .map((el) => el.value);
        if (discount.length) url.searchParams.set('discount', discount.join(','));
        else url.searchParams.delete('discount');

        url.searchParams.delete('page');
        window.location.href = url.toString();
    }

    onEach(nodeList, fn) {
        Array.from(nodeList || []).forEach(fn);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CatalogFilterSidebar();
});
