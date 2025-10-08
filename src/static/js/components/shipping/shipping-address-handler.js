import {BaseComponent} from '../../utils/components/BaseComponent.js';

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
            sPlaceId: '#summary-place-id'
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

        this.browserKey = this.layout.dataset.gplacesKey;
        this.pac = null;
        this.PlaceAutocompleteElement = null;

        this.init();
    }

    async bootstrapInitialState() {
        await this.loadMapsPlaces();
        this.mountAutocomplete();
        this.bindFieldMirrors();
        this.bindEvents();
        this.updateSummary();
    }

    setupBroadcastSubscriptions() {
    }

    async loadMapsPlaces() {
        if (this.PlaceAutocompleteElement) {
            return;
        }

        try {
            const {Loader} = await import('https://unpkg.com/@googlemaps/js-api-loader@1.16.2/dist/index.esm.js');

            const loader = new Loader({
                apiKey: this.browserKey,
                version: "weekly",
                libraries: ["places"]
            });

            const placesLibrary = await loader.importLibrary('places');
            this.PlaceAutocompleteElement = placesLibrary.PlaceAutocompleteElement;
        } catch (error) {
            throw error;
        }
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
            await place.fetchFields({fields: ['formattedAddress', 'addressComponents', 'id']});
            this.applyPlace(place);
        });

        this.pac.addEventListener('gmp-error', (e) => console.error('places widget error:', e));
    }

    bindEvents() {
        this.countrySelect.addEventListener('change', () => {
            this.mountAutocomplete();
            this.resetAddressFields();
        });
    }

    applyPlace(place) {
        const map = {};
        const comps = place.addressComponents || [];

        for (const c of comps) {
            for (const t of c.types) {
                if (!map[t]) map[t] = c;
            }
        }

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

        this.placeIdInput.value = place.id || '';
        this.addressInput.value = place.formattedAddress || '';
        this.streetInput.value = route;
        this.houseInput.value = number || (premise && !apartment ? premise : '');
        this.apartmentInput.value = apartment;
        this.cityInput.value = city;
        this.regionInput.value = region;
        this.postalInput.value = postal;

        this.updateSummaryFromFields(country);
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
        this.updateSummary();
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
}

document.addEventListener('DOMContentLoaded', () => {
    new ShippingAddressHandler();
});
