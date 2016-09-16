# -*- coding: utf-8 -*-
"""
    djam.global_request
    ~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

import json, string
from urlparse import urljoin

from cStringIO import StringIO

from django.utils.encoding import python_2_unicode_compatible
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from .utils import SharedStateBase

__all__ = ['get_request', 'get_session', 'flash', 'url_for', 'MessageBuffer']


class GlobalRequestMiddleware(SharedStateBase):
    """
    Record current django request in application 'shared state'.
    
    If a SCRIPT_NAME is set, correct PATH_INFO in case it starts with it.
    This is an **huggly hack** aiming at fixing consistent issues with
    PATH_INFO when SCRIPT_NAME is used... 
    ---

    IMPORTANT :
    ===========
        This middleware shall be deployed so that process_request can not be
        skipped, ie none of the middleware that will run before this one shall
        have a 'process_request' method that can return an HttpResponse...
    """

    def process_request(self, request):

        # record request in application shared state

        self._local.request = request

    def process_response(self, request, response):
        self._local.request = None
        return response


class _ExportRequest(SharedStateBase):
    def get_request(self):
        "return current request"

        return getattr(self._local, 'request', None)

    def get_session(self):
        "return current session"

        req = self.get_request()
        return req or req.session

# Construct get_request, get_session callables
_requestExporter = _ExportRequest()
get_request = _requestExporter.get_request
get_session = _requestExporter.get_session


class _MessageFlasher(SharedStateBase):
    """
    Allow to use django.contrib.messages
    without explicitely pulling the request...
    For this to work the GlobalRequestMiddleware shall be active
    ---
    Inspired by Flask wsgi framework
    """

    # Inline messages level constants
    DEBUG = messages.DEBUG
    INFO = messages.INFO
    SUCCESS = messages.SUCCESS
    WARNING = messages.WARNING
    ERROR = messages.ERROR

    _defaultLevel = messages.INFO

    def debug(self, msg):
        "wraps django.contrib.messages.debug..."
        self.__call__(msg, self.DEBUG)

    def info(self, msg):
        "wraps django.contrib.messages.info..."
        self.__call__(msg, self.INFO)

    def success(self, msg):
        "wraps django.contrib.messages.success..."
        self.__call__(msg, self.SUCCESS)

    def warning(self, msg):
        "wraps django.contrib.messages.warning..."
        self.__call__(msg, self.WARNING)

    def error(self, msg):
        "wraps django.contrib.messages.error..."
        self.__call__(msg, self.ERROR)

    def __call__(self, msg, level=None):
        "wraps django.contrib.messages.add_message..."
        level = level or getattr(msg, 'level', None) or self._defaultLevel
        messages.add_message(self._local.request, level, msg)

# Construct global flash object
flash = _MessageFlasher()


@python_2_unicode_compatible
class MessageBuffer(list):
    """
    _MessageFlasher helper allowing to construct a multiline message
    """

    _level = messages.INFO

    def get_level(self):
        return self._level

    def set_level(self, newlevel):
        if newlevel > self._level:
            self._level = newlevel

    level = property(get_level, set_level)

    def __str__(self):
        "return html multiline representation"

        return "<br/>".join([l for l in self])


def url_for(viewname, absolute=False, topurl=None, **reverseargs):
    """
    wraps django urlresolvers.reverse adding the possibility to make the url
    absolute retrieving host,port,scheme from current request...
    ---
    Inspired by Flask wsgi framework...
    """
    url = reverse(viewname, **reverseargs)
    if topurl:
        url = urljoin(topurl, url)
    if absolute:
        url = get_request().build_absolute_uri(url)
    return url
