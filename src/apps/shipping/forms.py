from django import forms
from django_countries.widgets import CountrySelectWidget

from .constants import EUROPEAN_COUNTRIES
from .models import Address, UserAddress


class AddressModelForm(forms.ModelForm):
    is_valid = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput())

    is_default = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'id': 'address-default', 'class': 'form-check-input'})
    )
    label = forms.CharField(
        max_length=64,
        initial='Home address',
        widget=forms.TextInput(attrs={
            'id': 'address-label', 'class': 'form-control',
            'placeholder': 'Label (e.g. Home address)'
        })
    )

    class Meta:
        model = Address
        fields = [
            'formatted',
            'country',
            'region',
            'city',
            'postal_code',
            'street',
            'house',
            'apartment',
            'place_id',
            'lat',
            'lng',
        ]
        widgets = {
            'formatted': forms.TextInput(attrs={
                'id': 'address-input', 'class': 'form-control',
                'placeholder': 'Start typing address', 'autocomplete': 'off'
            }),
            'country': CountrySelectWidget(attrs={
                'id': 'country-select', 'class': 'form-select'
            }),
            'street': forms.TextInput(attrs={'id': 'address-street', 'class': 'form-control'}),
            'house': forms.TextInput(attrs={'id': 'address-house', 'class': 'form-control'}),
            'apartment': forms.TextInput(attrs={'id': 'address-apartment', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'id': 'address-city', 'class': 'form-control'}),
            'region': forms.TextInput(attrs={'id': 'address-region', 'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'id': 'address-postal', 'class': 'form-control'}),
            'place_id': forms.HiddenInput(attrs={'id': 'address-place-id'}),
            'lat': forms.HiddenInput(attrs={'id': 'address-lat'}),
            'lng': forms.HiddenInput(attrs={'id': 'address-lng'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        european_codes = set(EUROPEAN_COUNTRIES)
        filtered_choices = []
        for country_code, country_name in self.fields['country'].choices:
            if country_code in european_codes or country_code == '':
                filtered_choices.append((country_code, country_name))
        self.fields['country'].choices = filtered_choices

        self._force_default = False
        if not UserAddress.objects.filter(user=user).exists():
            self._force_default = True
            self.fields['is_default'].initial = True
            self.initial['is_default'] = True
            self.fields['is_default'].widget.attrs['disabled'] = 'disabled'

    def clean_is_default(self):
        is_default = self.cleaned_data.get('is_default', False)
        if getattr(self, '_force_default', False):
            return True
        return is_default
