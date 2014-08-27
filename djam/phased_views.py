# -*- coding: utf-8 -*-
"""
    djam.phased_views
    ~~~~~~~~~~~~~~~~~

    Utilities that help defining 'phased' class based view


    :copyright: (c) 2012 by sc AmvTek srl
    :email: devel@amvtek.com
"""

from django.http import HttpResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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
    def lookup(meta, name, dicos):
        "search name in sequence of dictionary dicos..."

        for dic in dicos:
            value = dic.get(name)
            if value is not None:
                return value

    @classmethod
    def build_phased_request_handler(meta, verb):

        phaseList = "_{0}Phases".format(verb)

        def phased_handler(view, request):

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

        # build lookup list...
        dicos = [attrs]
        dicos.extend([b.__dict__ for b in bases])

        defaultPhases = meta.lookup('PHASES', dicos)

        for verb in View.http_method_names:

            # retrieve verb phases if set...
            param = "{0}_PHASES".format(verb.upper())
            verbPhases = meta.lookup(param, dicos) or defaultPhases

            if verbPhases is not None:

                # generates verb handler if not set...
                verbHandler = meta.lookup(verb, dicos)
                if verbHandler is None:
                    attrs[verb] = meta.build_phased_request_handler(verb)

                # rebuild _{verb}Phases list...
                l = []
                lname = "_{0}Phases".format(verb.lower())
                for phase in verbPhases:
                    if callable(phase):
                        l.append(phase)
                    else:
                        phaseFunc = meta.lookup(phase, dicos)
                        if not callable(phaseFunc):
                            errMsg = "missing callable for phase %s in %s" % \
                                     (phaseFunc, verb)
                            raise meta.UnknownCallable(errMsg)
                        l.append(phaseFunc)
                attrs[lname] = l

        # proceed with class construction
        return super(PhasedRequestProcessingMeta, meta).__new__(meta, name, bases, attrs)


class BaseApiRessource(View):
    """
    REST api ressource base class
    """

    __metaclass__ = PhasedRequestProcessingMeta

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(BaseApiRessource, self).dispatch(*args, **kwargs)
    
