import {BaseComponent} from '../../utils/components/BaseComponent.js';
import {MessageManager} from '../../utils/components/MessageManager.js';

class ShippingAddressHandler extends BaseComponent {
    constructor() {
        super({});

        this.selectors = {
            layout: '#shipping-layout',
            country: '#country-select',
            input: '#address-input',
            street: '#address-street',
            house: '#address-house',
            apartment: '#address-apartment',
            city: '#address-city',
            region: '#address-region',
            postal: '#address-postal',
            placeId: '#address-place-id',
            sFormatted: '#summary-formatted',
            sCountry: '#summary-country',
            sRegion: '#summary-region',
            sCity: '#summary-city',
            sPostal: '#summary-postal',
            sStreet: '#summary-street',
            sHouse: '#summary-house',
            sApartment: '#summary-apartment',
            sPlaceId: '#summary-place-id',
            lat: '#address-lat',
            lng: '#address-lng',
            flagImg: '.country-select-flag',
            submit: '#address-submit',
            isValid: '#id_is_valid'
        };

        this.layout = document.querySelector(this.selectors.layout);
        this.countrySelect = document.querySelector(this.selectors.country);
        this.addressInput = document.querySelector(this.selectors.input);
        this.streetInput = document.querySelector(this.selectors.street);
        this.houseInput = document.querySelector(this.selectors.house);
        this.apartmentInput = document.querySelector(this.selectors.apartment);
        this.cityInput = document.querySelector(this.selectors.city);
        this.regionInput = document.querySelector(this.selectors.region);
        this.postalInput = document.querySelector(this.selectors.postal);
        this.placeIdInput = document.querySelector(this.selectors.placeId);

        this.sFormatted = document.querySelector(this.selectors.sFormatted);
        this.sCountry = document.querySelector(this.selectors.sCountry);
        this.sRegion = document.querySelector(this.selectors.sRegion);
        this.sCity = document.querySelector(this.selectors.sCity);
        this.sPostal = document.querySelector(this.selectors.sPostal);
        this.sStreet = document.querySelector(this.selectors.sStreet);
        this.sHouse = document.querySelector(this.selectors.sHouse);
        this.sApartment = document.querySelector(this.selectors.sApartment);
        this.sPlaceId = document.querySelector(this.selectors.sPlaceId);
        this.latInput = document.querySelector(this.selectors.lat);
        this.lngInput = document.querySelector(this.selectors.lng);
        this.flagImg = document.querySelector(this.selectors.flagImg);

        this.submitBtn = document.querySelector(this.selectors.submit);
        this.isValidInput = document.querySelector(this.selectors.isValid);

        this.browserKey = this.layout.dataset.gplacesKey;
        this.mapFrame = document.getElementById('map-frame');
        this.pac = null;
        this.PlaceAutocompleteElement = null;

        this.init();
    }

    async bootstrapInitialState() {
        await this.loadMapsPlaces();
        this.mountAutocomplete();
        this.bindFieldMirrors();
        this.bindEvents();
        this.updateCountryFlagFromSelect();
        this.updateSummary();
        this.hideMap();
        this.setFormValidity(false);
    }

    setupBroadcastSubscriptions() {
    }

    async loadMapsPlaces() {
        if (this.PlaceAutocompleteElement) return;

        const {Loader} = await import(
            'https://unpkg.com/@googlemaps/js-api-loader@1.16.2/dist/index.esm.js'
            );

        const loader = new Loader({
            apiKey: this.browserKey,
            version: 'weekly',
            libraries: ['places']
        });

        const placesLibrary = await loader.importLibrary('places');
        this.PlaceAutocompleteElement = placesLibrary.PlaceAutocompleteElement;
    }

    mountAutocomplete() {
        if (this.pac) {
            this.pac.remove();
            this.pac = null;
        }

        const countryCode = this.countrySelect.value.toUpperCase();
        this.pac = new this.PlaceAutocompleteElement({includedRegionCodes: [countryCode]});
        this.pac.className = this.addressInput.className;
        this.pac.id = 'g-places-autocomplete';
        if (this.addressInput.placeholder) {
            this.pac.setAttribute('placeholder', this.addressInput.placeholder);
        }

        const parent = this.addressInput.parentElement;
        parent.insertBefore(this.pac, this.addressInput);
        this.addressInput.style.display = 'none';

        this.pac.addEventListener('gmp-select', async (e) => {
            const prediction = e.placePrediction;
            if (!prediction) return;
            const place = prediction.toPlace();
            await place.fetchFields({
                fields: ['formattedAddress', 'addressComponents', 'id', 'location', 'types']
            });
            this.applyPlace(place);
        });

        this.pac.addEventListener('gmp-error', (e) => console.error('places widget error:', e));
    }

    bindEvents() {
        this.countrySelect.addEventListener('change', () => {
            this.updateCountryFlagFromSelect();
            this.mountAutocomplete();
            this.resetAddressFields();
        });
    }

    applyPlace(place) {
        const map = {};
        const comps = place.addressComponents || [];
        for (const c of comps) for (const t of c.types) if (!map[t]) map[t] = c;

        const country = map.country ? map.country.shortText : '';
        const region1 = map.administrative_area_level_1 ? map.administrative_area_level_1.longText : '';
        const region2 = map.administrative_area_level_2 ? map.administrative_area_level_2.longText : '';
        const city =
            (map.locality && map.locality.longText) ||
            (map.postal_town && map.postal_town.longText) ||
            (map.sublocality && map.sublocality.longText) ||
            (map.administrative_area_level_3 && map.administrative_area_level_3.longText) || '';

        const route = map.route ? map.route.longText : '';
        const number = map.street_number ? map.street_number.longText : '';
        const postal = map.postal_code ? map.postal_code.longText : '';
        const premise = map.premise ? map.premise.longText : '';
        const subpremise = map.subpremise ? map.subpremise.longText : '';
        const apartment = subpremise || premise;
        const region = region1 || region2;

        const userHouse = this.houseInput.value.trim();

        this.placeIdInput.value = place.id || '';
        this.addressInput.value = place.formattedAddress || '';
        this.streetInput.value = route;
        this.houseInput.value = number || (premise && !apartment ? premise : userHouse);
        this.apartmentInput.value = apartment;
        this.cityInput.value = city;
        this.regionInput.value = region;
        this.postalInput.value = postal;

        if (place.location && this.latInput && this.lngInput) {
            const latVal = typeof place.location.lat === 'function'
                ? place.location.lat()
                : place.location.lat;
            const lngVal = typeof place.location.lng === 'function'
                ? place.location.lng()
                : place.location.lng;
            this.latInput.value = latVal;
            this.lngInput.value = lngVal;
        } else {
            if (this.latInput) this.latInput.value = '';
            if (this.lngInput) this.lngInput.value = '';
        }

        const hasStreet = !!route;
        const hasHouse = !!number;
        const hasCity = !!city;
        const hasRegion = !!region;
        const houseMatches = userHouse ? userHouse === number : true;

        const flags = {
            street: !hasStreet,
            house: !hasHouse || !houseMatches,
            city: !hasCity,
            region: !hasRegion
        };

        const messages = [];
        if (!hasStreet) messages.push('Enter street');
        if (!hasHouse) messages.push('Enter house number');
        if (hasHouse && !houseMatches) {
            messages.push('House number does not match the selected address');
        }
        if (!hasCity) messages.push('Enter city');
        if (!hasRegion) messages.push('Enter region/state');

        this.markInvalidFields(flags, messages);

        const verified = hasStreet && hasHouse && hasCity && hasRegion && houseMatches;
        this.updateSummaryFromFields(country);
        this.renderMapFromPlace(place, verified);
        this.setFormValidity(verified);
    }

    renderMapFromPlace(place, verified) {
        if (!this.mapFrame) return;
        const key = this.mapFrame.dataset.embedKey || this.browserKey || '';
        const pid = place && place.id ? place.id : '';
        const loc = place && place.location ? place.location : null;

        let src = '';

        if (key && verified && pid) {
            const q = 'place_id:' + pid;
            src =
                'https://www.google.com/maps/embed/v1/place?key=' +
                encodeURIComponent(key) +
                '&q=' +
                encodeURIComponent(q);
        } else if (key && loc) {
            const lat = typeof loc.lat === 'function' ? loc.lat() : loc.lat;
            const lng = typeof loc.lng === 'function' ? loc.lng() : loc.lng;
            src =
                'https://www.google.com/maps/embed/v1/view?key=' +
                encodeURIComponent(key) +
                '&center=' +
                lat +
                ',' +
                lng +
                '&zoom=16';
        }

        if (src) {
            this.mapFrame.src = src;
            this.showMap();
        }
    }

    markInvalidFields(flags, messages) {
        this.clearAllInvalid();
        if (flags.street) this.setInvalid(this.streetInput, 'Invalid street', true);
        if (flags.house) this.setInvalid(this.houseInput, 'Invalid house number', true, true);
        if (flags.city) this.setInvalid(this.cityInput, 'Invalid city', true);
        if (flags.region) this.setInvalid(this.regionInput, 'Invalid region/state', true);
        if (messages && messages.length) {
            MessageManager.showGlobalMessage(messages.join('. ') + '.', 'warning');
        }
        this.setFormValidity(false);
    }

    setInvalid(input, message, silent = false, clearValue = false) {
        input.classList.add('is-invalid');
        if (clearValue) input.value = '';
        if (typeof input.setCustomValidity === 'function') {
            input.setCustomValidity(message || 'Invalid');
        }
        if (!silent) MessageManager.showGlobalMessage(message || 'Invalid address field', 'warning');
        if (typeof input.reportValidity === 'function') input.reportValidity();
    }

    clearInvalid(input) {
        input.classList.remove('is-invalid');
        if (typeof input.setCustomValidity === 'function') input.setCustomValidity('');
    }

    clearAllInvalid() {
        this.clearInvalid(this.streetInput);
        this.clearInvalid(this.houseInput);
        this.clearInvalid(this.cityInput);
        this.clearInvalid(this.regionInput);
        this.clearInvalid(this.postalInput);
    }

    hideMap() {
        if (!this.mapFrame) return;
        this.mapFrame.hidden = true;
        this.mapFrame.removeAttribute('src');
    }

    showMap() {
        if (!this.mapFrame) return;
        this.mapFrame.hidden = false;
    }

    setFormValidity(verified) {
        if (this.submitBtn) this.submitBtn.disabled = !verified;
        if (this.isValidInput) this.isValidInput.value = verified ? 'true' : 'false';
    }

    updateSummaryFromFields(country = '') {
        this.sFormatted.textContent = this.addressInput.value;
        this.sCountry.textContent = country || this.countrySelect.value;
        this.sRegion.textContent = this.regionInput.value;
        this.sCity.textContent = this.cityInput.value;
        this.sPostal.textContent = this.postalInput.value;
        this.sStreet.textContent = this.streetInput.value;
        this.sHouse.textContent = this.houseInput.value;
        this.sApartment.textContent = this.apartmentInput.value;
        this.sPlaceId.textContent = this.placeIdInput.value;
    }

    bindFieldMirrors() {
        const mirror = (el, target) => {
            el.addEventListener('input', () => {
                target.textContent = el.value;
            });
        };

        mirror(this.streetInput, this.sStreet);
        mirror(this.houseInput, this.sHouse);
        mirror(this.apartmentInput, this.sApartment);
        mirror(this.cityInput, this.sCity);
        mirror(this.regionInput, this.sRegion);
        mirror(this.postalInput, this.sPostal);

        const invalidate = () => this.setFormValidity(false);
        [this.streetInput, this.houseInput, this.cityInput, this.regionInput, this.postalInput]
            .forEach((el) => el && el.addEventListener('input', invalidate));
    }

    resetAddressFields() {
        this.addressInput.value = '';
        this.streetInput.value = '';
        this.houseInput.value = '';
        this.apartmentInput.value = '';
        this.cityInput.value = '';
        this.regionInput.value = '';
        this.postalInput.value = '';
        this.placeIdInput.value = '';
        if (this.latInput) this.latInput.value = '';
        if (this.lngInput) this.lngInput.value = '';

        this.clearAllInvalid();
        this.updateSummary();
        this.hideMap();
        this.setFormValidity(false);
    }

    updateSummary() {
        this.sFormatted.textContent = '';
        this.sCountry.textContent = this.countrySelect.value || '';
        this.sRegion.textContent = this.regionInput.value || '';
        this.sCity.textContent = this.cityInput.value || '';
        this.sPostal.textContent = this.postalInput.value || '';
        this.sStreet.textContent = this.streetInput.value || '';
        this.sHouse.textContent = this.houseInput.value || '';
        this.sApartment.textContent = this.apartmentInput.value || '';
        this.sPlaceId.textContent = this.placeIdInput.value || '';
    }

    updateCountryFlagFromSelect() {
        if (!this.flagImg || !this.countrySelect) return;

        const basePath = '/static/flags/';
        const placeholder = basePath + '__.gif';

        const rawCode = (this.countrySelect.value || '').trim();
        const code = rawCode ? rawCode.toLowerCase() : '';

        const nextSrc = code ? basePath + code + '.gif' : placeholder;

        this.flagImg.onerror = () => {
            this.flagImg.onerror = null;
            this.flagImg.src = placeholder;
        };

        this.flagImg.src = nextSrc;
        this.flagImg.alt = code ? `Flag ${rawCode}` : 'No flag';
        this.flagImg.title = this.countrySelect.options[
            this.countrySelect.selectedIndex
            ]?.text || '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ShippingAddressHandler();
});
