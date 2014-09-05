# -*- coding: utf-8 -*-
"""
    djam.utils
    ~~~~~~~~~~

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""

import os, re, hashlib, threading, string

from binascii import hexlify

from django.conf import settings

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
    buf = StringIO(rId)
    parts = [buf.read(s) for i in xrange(lId / s)]
    return sep.join(parts)


def h2r(humId):
    """
    remove formatting separators from readability enhanced identifier
    """
    return humId.translate(None, _SEPARATORS)