# -*- coding: utf-8 -*-
"""
    djam.world_countries
    ~~~~~~~~~~~~~~~~~~~~

    Utilities to guess or define country...

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django import forms
from django.utils.translation import get_language

from .global_request import get_request

DEFAULT_COUNTRY = getattr(settings, 'DEFAULT_COUNTRY', 'US')

def guess_request_country(request):
    "Try to guess request country"

    # Option 01 : use GEOIP country
    geoipCountry = request and request.META.get('HTTP_X_GEOIP_COUNTRY')
    if geoipCountry is not None:
        return geoipCountry

    # Option 02 : reverse language based on optional LANG_COUNTRY setting...
    if hasattr(settings, 'LANG_COUNTRY'):
        lang = get_language()
        return settings.LANG_COUNTRY.get(lang, DEFAULT_COUNTRY)

    # Option 03 : fallback to DEFAULT_COUNTRY
    return DEFAULT_COUNTRY

class CountrySelectField(forms.ChoiceField):
    "Provide World Country list with names in current_user language"

    __country_list_cache = {}

    @classmethod
    def _get_localized_country_list(cls, localeKey):
        
        import pytz, babel # define dependencies version...
        
        cache = cls.__country_list_cache  # local alias
        countries = cache.get(localeKey)
        if countries is None:

            COUNTRIES = cache.get('_COUNTRIES')
            if COUNTRIES is None:
                COUNTRIES = frozenset(pytz.country_names.keys())
                cache['_COUNTRIES'] = COUNTRIES

            locale = babel.Locale.parse(localeKey)
            countries = [(k, v) for k, v in locale.territories.items() if k in COUNTRIES]
            countries.sort(key=lambda t: t[1])
            cache[localeKey] = countries

        return countries

    def __deepcopy__(self, memo):
        "overwritten as this get called each time forms are instantiated"

        rv = super(CountrySelectField, self).__deepcopy__(memo)
        lang = getattr(get_request(), "LANGUAGE_CODE", settings.LANGUAGE_CODE)
        rv.choices = self._get_localized_country_list(lang)
        return rv
