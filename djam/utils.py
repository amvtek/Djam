# -*- coding: utf-8 -*-
"""
    djam.utils
    ~~~~~~~~~~

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, division

import os, re, hashlib, threading, string
from binascii import hexlify

from django.conf import settings
from django.utils import six

class SharedStateBase(object):
    "Allow all instances to 'reliably' share variables"

    # Use the 'Borg pattern' to share state between all instances.
    # See source code of django.db.models.loading for example...
    __shared_state = dict(

        # instances may use this to share variables on a per thread basis
        _local=threading.local(),

    )

    def __init__(self):
        "I shall always be called"

        self.__dict__ = self.__shared_state


class SettingRename(object):

    def __init__(self, settingFmt):
        
        self.settingFmt = settingFmt

    def __call__(self, name):
        """
        Check if a setting has been defined to overwrite name
        returns setting if it exist or name...
        """

        setting4name = self.settingFmt(name.upper())
        overwrite = getattr(settings, setting4name, None)
        return overwrite or name


def calculate_password_verifier(password, seed=None, hmethod='sha1'):
    # make sure password is not empty
    password = password.strip()
    if not password:
        raise ValueError("can not use empty password")

    h = getattr(hashlib, hmethod)()

    if seed is None:
        seed = hexlify(os.urandom(h.digest_size))
    h.update(seed)

    h.update(password)

    return "$".join([hmethod, seed, h.hexdigest()])


class FolderLoader(object):
    "Provide a callable that load file content from a Folder"

    def __init__(self, refFileName):
        self.baseFolder = os.path.dirname(os.path.abspath(refFileName))
        if not os.path.exists(self.baseFolder):
            raise ValueError(
                "Unable to resolve containing folder for %s" % refFileName
            )

    def load(self, filename):
        f = open(os.path.join(self.baseFolder, filename), 'r')
        return f.read()

def get_cbv_object(viewfunc):
    """
    If viewfunc has been obtained using CBV.as_view(**initkwargs) factory
    returns instance of CBV that viewfunc will construct each time it is called
    """
    
    if getattr(viewfunc, '__closure__', None) is None:
        # viewfunc has not been constructed using CBV
        return

    try:
        
        # We assume that viewfunc was returned by CBV.as_view(**initkwargs)
        # we try to retrieve CBV class & initkwargs
        #
        # this approach is **fragile** as it rely on inner variable names, 
        # used in base as_view implementation
        ctx = dict(zip(view.__code__.co_freevars,
            [c.cell_contents for c in (view.__closure__ or [])]
            ))
        initkwargs = ctx.get('initkwargs') or {}
        CBV = ctx.get('cls')
        
        if callable(CBV):
            return CBV(**initkwargs)

    except:

        return None


_STEPS = range(4, 0, -1)  # cache possible formatting steps
_SEPARATORS = string.whitespace + "_-"

def r2h(rawId, sep=" "):
    """
    return readability enhanced identifier
    by inserting a separator every n characters
    """
    rId = str(rawId).strip()
    lId = len(rId)
    for s in _STEPS:
        if lId % s == 0:
            break
    if s == 1:
        return rId
    buf = six.StringIO(rId)
    parts = [buf.read(s) for i in range(lId // s)]
    return sep.join(parts)

if six.PY2:
    
    from django.utils.encoding import force_bytes, force_text

    translate = string.translate
    
    def h2r(humId):
        """
        remove formatting separators from readability enhanced identifier
        """
        
        return force_text(translate(force_bytes(humId), None, _SEPARATORS))

else:

    # TODO: works on Python 3 support...
    def h2r(humId):

        raise NotImplementedError("no implementation for Python 3")
