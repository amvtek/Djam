# -*- coding: utf-8 -*-
"""
    djam.phased_views
    ~~~~~~~~~~~~~~~~~

    Utilities that help defining 'phased' class based view


    :copyright: (c) sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

import re, json

from django.http import HttpResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import six

class PhasedRequestProcessingMeta(type):
    """
    Metaclass that :

        * Generates default implementation for {verb} (get,head,post,put..)
        methods if :
            1. method is not defined and can not be inherited.
            2. class contains {VERB}_PHASES or PHASES parameter

        * 'Compiles' encountered {VERB}_PHASES or PHASES parameter into
        _{verb}Phases list of callables  
    """

    class UnknownCallable(Exception):
        "raised in case we are unable to resolve handler name to a callable..."
        pass

    
    @classmethod
    def make_lookup(meta, bases, attrs):
        "return lookup callable"

        MISSING = object()

        def lookup(name):

            # search in attrs dict
            rv = attrs.get(name, MISSING)
            if rv != MISSING:
                return rv

            # search in bases
            for base in bases:
                rv = getattr(base, name, MISSING)
                if rv != MISSING:
                    return rv

        return lookup


    @classmethod
    def build_phased_request_handler(meta, verb):

        phaseList = "_{0}Phases".format(verb)

        def phased_handler(view, request, *args, **kwargs):

            handlers = getattr(view, phaseList)

            resp = request
            for handler in handlers:
                resp = handler(view, resp) or resp
                if isinstance(resp, HttpResponse):
                    return resp

        # add documentation
        doc = "process request by phases using callables in %s" % phaseList
        phased_handler.__doc__ = doc

        return phased_handler

    def __new__(meta, name, bases, attrs):

        # build lookup func
        lookup = meta.make_lookup(bases, attrs)

        defaultPhases = lookup('PHASES')

        for verb in View.http_method_names:

            # retrieve verb phases if set...
            param = "{0}_PHASES".format(verb.upper())
            verbPhases = lookup(param) or defaultPhases

            if verbPhases is not None:

                # generates verb handler if not set...
                verbHandler = lookup(verb)
                if verbHandler is None:
                    attrs[verb] = meta.build_phased_request_handler(verb)

                # rebuild _{verb}Phases list...
                l = []
                lname = "_{0}Phases".format(verb.lower())
                for phase in verbPhases:
                    if callable(phase):
                        l.append(phase)
                    else:
                        phaseFunc = lookup(phase)
                        if not callable(phaseFunc):
                            errMsg = "missing callable for phase %s in %s" % \
                                     (phase, verb)
                            raise meta.UnknownCallable(errMsg)
                        l.append(phaseFunc)
                attrs[lname] = l

        # proceed with class construction
        return super(PhasedRequestProcessingMeta, meta).__new__(meta, name, bases, attrs)


class BaseApiResource(six.with_metaclass(PhasedRequestProcessingMeta, View)):
    """
    REST api resource base class
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(BaseApiResource, self).dispatch(*args, **kwargs)

    _is_json = staticmethod(re.compile('/json').search)

    def load_body(self, request):
        """
        deserialize request.body in request.POST & request.FILES
        """

        if not (request.POST or request.FILES):

            contenttype = request.META.get("CONTENT_TYPE","")
            
            if self._is_json(contenttype):

                request.POST = json.loads(request.body)

            elif request.method != 'POST':

                # save actual method (eg PUT...)
                method = request.method

                try:

                    # trick Django in believing this is a POST
                    request.method = 'POST'
                    request._load_post_and_files()

                finally:

                    # restore method
                    request.method = method

    load_json = load_body
