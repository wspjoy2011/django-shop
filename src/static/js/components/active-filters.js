class ActiveFilters {
    constructor() {
        this.container = document.getElementById('activeFiltersContainer');
        this.header = document.getElementById('activeFiltersHeader');
        this.content = document.getElementById('activeFiltersContent');
        this.countBadge = document.getElementById('activeFiltersCount');
        this.clearAllBtn = document.getElementById('clearAllFilters');
        this.toggleBtn = document.getElementById('toggleActiveFilters');

        this.filterConfig = {
            gender: {
                param: 'gender',
                container: 'genderFilterTags',
                group: 'genderFiltersGroup',
                labels: this.getGenderLabels()
            },
            season: {
                param: 'season',
                container: 'seasonFilterTags',
                group: 'seasonFiltersGroup',
                labels: this.getSeasonLabels()
            },
            availability: {
                param: 'availability',
                container: 'availabilityFilterTags',
                group: 'availabilityFiltersGroup',
                labels: {
                    'available': 'Available',
                    'out_of_stock': 'Out of Stock',
                    'not_active': 'Not Active'
                }
            },
            discount: {
                param: 'discount',
                container: 'discountFilterTags',
                group: 'discountFiltersGroup',
                labels: {
                    'on_sale': 'On Sale',
                    'no_discount': 'No Discount'
                }
            },
            price: {
                param: ['min_price', 'max_price'],
                container: 'priceFilterTags',
                group: 'priceFiltersGroup'
            }
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.render();
    }

    bindEvents() {
        this.header.addEventListener('click', () => this.toggleCollapse());

        this.clearAllBtn.addEventListener('click', () => this.clearAllFilters());

        document.querySelectorAll('[data-clear-group]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const group = btn.dataset.clearGroup;
                this.clearFilterGroup(group);
            });
        });
    }

    getGenderLabels() {
        return {
            'Men': 'Men',
            'Women': 'Women',
            'Boys': 'Boys',
            'Girls': 'Girls',
            'Unisex': 'Unisex'
        };
    }

    getSeasonLabels() {
        const seasonOptions = document.querySelectorAll('[data-season-option]');
        const labels = {};
        seasonOptions.forEach(option => {
            const slug = option.dataset.seasonSlug;
            const name = option.dataset.seasonName;
            if (slug && name) {
                labels[slug] = name;
            }
        });
        return labels;
    }

    getCurrentFilters() {
        const url = new URL(window.location.href);
        const filters = {};

        Object.keys(this.filterConfig).forEach(key => {
            const cfg = this.filterConfig[key];
            if (key === 'price') return;

            const value = url.searchParams.get(cfg.param);
            if (value) {
                filters[key] = value.split(',').filter(v => v.trim());
            }
        });

        return filters;
    }

    render() {
        const filters = this.getCurrentFilters();
        const hasFilters = Object.keys(filters).length > 0;

        if (!hasFilters && !this.hasPriceFilters()) {
            this.container.style.display = 'none';
            return;
        }

        this.container.style.display = 'block';

        let totalCount = 0;

        Object.keys(this.filterConfig).forEach(key => {
            if (key === 'price') return;

            const config = this.filterConfig[key];
            const values = filters[key] || [];
            const group = document.getElementById(config.group);
            const container = document.getElementById(config.container);

            if (values.length > 0) {
                totalCount += values.length;
                group.style.display = 'block';
                container.innerHTML = this.renderFilterTags(key, values, config.labels);
            } else {
                group.style.display = 'none';
                if (container) container.innerHTML = '';
            }
        });

        totalCount += this.renderPriceChips();

        this.countBadge.textContent = totalCount;
        this.clearAllBtn.style.display = totalCount > 0 ? 'block' : 'none';
    }

    hasPriceFilters() {
        const url = new URL(window.location.href);
        return url.searchParams.has('min_price') || url.searchParams.has('max_price');
    }

    renderPriceChips() {
        const url = new URL(window.location.href);
        const min = url.searchParams.get('min_price');
        const max = url.searchParams.get('max_price');

        const group = document.getElementById('priceFiltersGroup');
        const container = document.getElementById('priceFilterTags');

        if (!group || !container) return 0;

        const chips = [];
        if (min) {
            chips.push(`
                <a href="#" class="filter-tag" data-remove-filter="price" data-filter-value="min_price">
                    From $${parseFloat(min).toFixed(2)}
                    <i class="fas fa-times remove-icon"></i>
                </a>
            `);
        }
        if (max) {
            chips.push(`
                <a href="#" class="filter-tag" data-remove-filter="price" data-filter-value="max_price">
                    To $${parseFloat(max).toFixed(2)}
                    <i class="fas fa-times remove-icon"></i>
                </a>
            `);
        }

        if (chips.length) {
            group.style.display = 'block';
            container.innerHTML = chips.join('');
            return chips.length;
        } else {
            group.style.display = 'none';
            container.innerHTML = '';
            return 0;
        }
    }

    renderFilterTags(filterType, values, labels) {
        return values.map(value => {
            const label = labels[value] || value;
            return `
                <a href="#" class="filter-tag" data-remove-filter="${filterType}" data-filter-value="${value}">
                    ${label}
                    <i class="fas fa-times remove-icon"></i>
                </a>
            `;
        }).join('');
    }

    toggleCollapse() {
        const isCollapsed = this.container.classList.contains('collapsed');

        if (isCollapsed) {
            this.container.classList.remove('collapsed');
            this.toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
        } else {
            this.container.classList.add('collapsed');
            this.toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
        }
    }

    clearAllFilters() {
        const url = new URL(window.location.href);

        Object.keys(this.filterConfig).forEach(key => {
            const param = this.filterConfig[key].param;
            if (Array.isArray(param)) {
                param.forEach(p => url.searchParams.delete(p));
            } else {
                url.searchParams.delete(param);
            }
        });

        url.searchParams.delete('page');
        window.location.href = url.toString();
    }

    clearFilterGroup(filterType) {
        const config = this.filterConfig[filterType];
        const url = new URL(window.location.href);

        if (Array.isArray(config.param)) {
            config.param.forEach(p => url.searchParams.delete(p));
        } else {
            url.searchParams.delete(config.param);
        }

        url.searchParams.delete('page');
        window.location.href = url.toString();
    }

    removeFilter(filterType, value) {
        const config = this.filterConfig[filterType];
        const url = new URL(window.location.href);

        if (filterType === 'price') {
            url.searchParams.delete(value);
        } else {
            const currentValues = url.searchParams.get(config.param);
            if (currentValues) {
                const values = currentValues.split(',').filter(v => v.trim() !== value);

                if (values.length > 0) {
                    url.searchParams.set(config.param, values.join(','));
                } else {
                    url.searchParams.delete(config.param);
                }
            }
        }

        url.searchParams.delete('page');
        window.location.href = url.toString();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const activeFilters = new ActiveFilters();

    document.addEventListener('click', (e) => {
        if (e.target.closest('[data-remove-filter]')) {
            e.preventDefault();
            const tag = e.target.closest('[data-remove-filter]');
            const filterType = tag.dataset.removeFilter;
            const value = tag.dataset.filterValue;
            activeFilters.removeFilter(filterType, value);
        }
    });
});
