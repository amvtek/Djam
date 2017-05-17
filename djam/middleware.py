# -*- coding: utf-8 -*-
"""
    djam.middleware
    ~~~~~~~~~~~~~~~

    Various django middleware

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

def InstallJavascriptCatalog(get_response=None):
    """
    Middleware ensuring that 'django.views.i18n.javascript_catalog' is wired.
    This middleware can be configured using settings :
        * JSI18N_PACKAGES : default is ()
        * JSI18N_VIEWNAME : default is 'jsi18n'
        * JSI18N_USE_I18NPATTERN : default is True
    """

    import django.core.urlresolvers as URL
    jsi18nView = "django.views.i18n.javascript_catalog"

    try:

        # check if javascript_catalog exists in settings.ROOT_URLCONF
        URL.reverse(jsi18nView)

    except URL.NoReverseMatch :

        # we fix ROOT_URLCONF urlpatterns...

        if getattr(settings,'JSI18N_USE_I18NPATTERN',True):

            from django.conf.urls.i18n import i18n_patterns as patterns
        else:

            from django.conf.urls import patterns

        resolver = URL.get_resolver(None)

        # define missing jsi18npatterns ...
        jsi18nParams = dict(packages=getattr(settings,'JSI18N_PACKAGES',()))
        jsi18nViewName = getattr(settings,'JSI18N_VIEWNAME',"jsi18n")
        jsi18npatterns = patterns('',
                (r"^jsi18n$",jsi18nView,jsi18nParams,jsi18nViewName),
                )

        # correct default urlpatterns
        urlpatterns = resolver.urlconf_module.urlpatterns
        urlpatterns += jsi18npatterns
        resolver.urlconf_module.urlpatterns = urlpatterns

        # reset resolver
        for cachename in ['_reverse_dict','_namespace_dict','_app_dict']:
            setattr(resolver,cachename,{})

    raise MiddlewareNotUsed()
