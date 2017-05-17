# -*- coding: utf-8 -*-
"""
    djam.cors
    ~~~~~~~~~

    middleware that helps supporting W3C Cross-Origin Resource Sharing

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django.http import HttpResponse

from .utils import get_cbv_object

# See : http://www.w3.org/TR/cors/#simple-method
CORS_SIMPLE_METHODS = frozenset(['GET', 'HEAD', 'POST'])

# See : http://www.w3.org/TR/cors/#simple-header
CORS_SIMPLE_HEADERS = frozenset([
    'Cache-Control', 'Content-Language',
    'Content-Type', 'Expires',
    'Last-Modified', 'Pragma'
    ])

class CORSMiddleware(object):

    # To redefine options in this default policy
    # Provide settings DEFAULT_CORS_POLICY
    # and/or set custom cors_policy on your views
    #
    # This middleware determines current view cors_policy
    # taking in consideration cors_policy options
    # encountered in view > settings > this middleware...
    default_cors_policy = {

        #
        # enabled option
        # 
        # for this middleware to act
        # enabled shall be set to True
        'enabled': False,

        #
        # allow_origin option
        #
        # CORS request always contain an Origin header
        # middleware will check received Origin against configured allow_origin
        #
        # Use '*' to allow all origins
        # Otherwise provides 'white list' of allowed origins
        # origin are defined as scheme://host[:port]
        # eg allow_origin: ['http://example.com', 'https://bar.foo.com:8967']
        'allow_origin': '*',

        #
        # allow_credentials option
        #
        # by default User-Agent prevent CORS request to exchange cookies
        # & authorization with remote view
        #
        # set True to allow exchanging cookies & authorization
        'allow_credentials': False,
        
        # 
        # expose_headers option
        #
        # by default User-Agent does not transmit special headers contained
        # in CORS request responses.
        #
        # whitelist the response headers which you want to transmit to CORS
        # request issuer 
        'expose_headers': None,
        
        #
        # allow_methods option
        #
        # preflight CORS request shall contain an Access-Control-Request-Method
        # header, which define name of method to be authorized. If server can
        # match transmitted method against what allow_methods contains, it will
        # add to preflight response the Access-Control-Allow-Methods header
        # which list all the authorized methods...
        #
        # whitelist methods to be allowed optionally omitting the OPTIONS one
        # which is used to transmit preflight request
        'allow_methods': ['GET', 'HEAD', 'POST'],

        #
        # allow_headers option
        #
        # preflight CORS request may contain an Access-Control-Request-Headers
        # header, which list special headers that will be transmitted in main
        # request. If server can match all transmitted headers against what
        # allow_headers contains, it will add to preflight response the
        # Access-Control-Allow-Headers header which list all authorized
        # headers...
        #
        # Use '*' to allow transmission of any special header
        # Otherwise provides 'white list' of allowed special headers
        'allow_headers': '*',

        #
        # max_age option
        #
        # To prevent having to send preflight request before each CORS request,
        # User-Agent may maintain a preflight cache, which will be used to
        # cache preflight response. If max_cache option is set, preflight
        # response will contain the Access-Control-Max-Age header which value
        # is set max_cache

        # time in seconds during which UserAgent may cache preflight response
        'max_age': 0,
    }

    def __init__(self, get_response=None):
        self.get_response = get_response

    def get_cors_policy(self, view):
        "return cors_policy dictionary"

        opts = self.default_cors_policy.copy()

        # update using settings DEFAULT_CORS_POLICY
        sopts = getattr(settings,'DEFAULT_CORS_POLICY',None)
        if sopts:
            opts.update(sopts)

        # update using view cors_policy
        
        pn = 'cors_policy' # local alias
        cbvobj = get_cbv_object(view)

        vopts = getattr(view, pn, None) or getattr(cbvobj, pn, None) or {}
        if cbvobj and 'allow_methods' not in vopts:
            methods = getattr(cbvobj, 'http_method_names', None)
            if methods:
                vopts['allow_methods'] = [m.upper() for m in methods]
        
        opts.update(vopts)

        return opts

    def process_view(self, request, view, args, kwargs):

        origin = request.META.get('HTTP_ORIGIN')

        # abort if origin is not set
        if origin is None:
            return
        
        # retrieve CORS policy for current view
        cors = self.get_cors_policy(view)

        # abort if view is not CORS enabled...
        if not cors.get('enabled'):
            return

        # prepare list of CORS headers that will be added to response
        cors_headers = []

        # abort if request origin is not allowed 
        allowed_origins = cors.get('allow_origin') or []
        if allowed_origins == "*" or origin in allowed_origins:
            cors_headers.append(('Access-Control-Allow-Origin',origin))
        else:
            return

        # optionally add Access-Control-Allow-Credentials to cors_headers
        if cors.get('allow_credentials'):
            cors_headers.append(('Access-Control-Allow-Credentials','true'))

        # optionally process OPTIONS request assuming they are preflight
        if request.method == 'OPTIONS':


            # retrieve preflighted method & abort if it is not set
            prfM = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')
            if prfM is None:
                return

            # abort if preflighted method is not allowed
            # W3C spec call for case sensitive match
            allowed_methods = set(cors.get('allow_methods') or [])
            if prfM not in allowed_methods:
                return

            # add Access-Control-Allow-Methods to cors_headers
            allowed_methods.add('OPTIONS')
            am = ",".join(allowed_methods)
            cors_headers.append(('Access-Control-Allow-Methods', am))

            # retrieve optional preflighted headers list & parse it
            prfH = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')
            prfH = set([h.strip().title() for h in (prfH or '').split(',')])
            if '' in prfH:
                prfH.remove('')

            # retrieve & normalize list of allowed headers
            alwdH = cors.get('allow_headers') or []
            if alwdH == '*':
                alwdH = prfH
            else:
                alwdH = set([h.strip().title() for h in alwdH])

            # abort if any of the preflighted headers is not allowed
            # W3C spec calls for case insensitive match
            # hence all headers have been normalized prior to comparison
            if not prfH.issubset(alwdH):
                return

            # add Access-Control-Allow-Headers to cors_headers
            cors_headers.append(('Access-Control-Allow-Headers',",".join(prfH)))

            # optionally add Access-Control-Max-Age to cors_headers
            maxage = cors.get('max_age')
            if maxage:
                cors_headers.append(('Access-Control-Max-Age',maxage))

            # directly serve this request if view does not support OPTIONS
            vmethods = getattr(view,'http_method_names',None) or []
            if 'options' not in vmethods:
                request.cors_headers = cors_headers
                return HttpResponse()
        
        # mark request so that cors_headers are later added to response
        request.cors_headers = cors_headers

        # optionally Add Access-Control-Expose-Headers to cors_headers
        expH = cors.get('expose_headers')
        if expH:
            expH = ",".join([h.strip().title() for h in expH])
            cors_headers.append(('Access-Control-Expose-Headers',expH))

    def process_response(self, request, response):
        "Optionally add CORS headers to response..."

        cors_headers = getattr(request, 'cors_headers', None)
        
        if cors_headers:
            for hdr,val in cors_headers:
                response[hdr] = val

        return response

    def __call__(self, request):
        "django >= 1.10 middleware entry point"

        # TODO: 
        # django >= 1.10 keep on calling process_view 
        # so normally get_response accounts for process_view (not tested yet)

        response = self.get_response(request)

        return self.process_response(request, response)
