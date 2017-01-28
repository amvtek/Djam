# -*- coding: utf-8 -*-
"""
    djam.thumbnailer
    ~~~~~~~~~~~~~~~~

    Exports Thumbnailer class based view

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

import re
from os.path import splitext

from PIL import Image, ImageOps

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.views.generic.base import View
from django.http import HttpResponse, HttpResponseNotFound

_parseThumbRegex = re.compile(r"\s*([0-9a-zA-Z/]+)-w(\d+)-h(\d+)\.(\w+)")

def parse_thumbnail_infos(filename):
    "return mastername,extension,(width,height)..."

    m = _parseThumbRegex.match(filename)

    if m is not None:
        mastername = "%s.%s" % (m.group(1), m.group(4))
        extension = m.group(4)
        size = (int(m.group(2)), int(m.group(3)))
        return mastername, extension, size


def build_thumbnail_path(mpath, width, height=None):
    "return path encoding thumbnail dimensions"

    # validate dimensions
    width = int(width)
    height = int(height or width)

    # extracts basename, extension from mpath
    m = _parseThumbRegex.match(mpath)
    if m is not None:
        basename = m.group(1)
        extension = ".%s" % m.group(4)
    else:
        basename, extension = splitext(mpath)

    return "%(basename)s-w%(width)i-h%(height)i%(extension)s" % locals()


class Thumbnailer(View):
    """
    View class that generates a thumbnail from an image retrieved from storage.
    Desired Thumbnail dimension are extracted from url path.

    Generated thumbnails maybe cached and served by a 'static' webserver such
    as Nginx or Apache... 
    """

    storage = default_storage
    
    saveThumbnail = getattr(settings,'THUMBNAIL_SAVE',False)
    
    lifetime = getattr(settings,'THUMBNAIL_CACHE_TIME', 900 ) # 900 sec = 15 mn
    

    def get(self, request, path):

        filename = path
        name, ext = filename.split(".")

        # returns file if it is currently in the storage
        if self.storage.exists(filename):
            picfile = self.storage.open(filename)
            resp = HttpResponse(content=picfile, content_type="image/%s" % ext)
            resp["Cache-Control"] = 'max-age=%s' % self.lifetime
            return resp

        # if file not in storage it may encode thumbnail dimensions
        rv = parse_thumbnail_infos(filename)
        if rv is None:
            return HttpResponseNotFound()
        mastername, ext, targetSize = rv

        if not self.storage.exists(mastername):
            return HttpResponseNotFound()
        try:
            picture = Image.open(self.storage.open(mastername))
        except IOError:
            return HttpResponseNotFound()

        resp = HttpResponse(content_type="image/%s" % ext)
        resp["Cache-Control"] = 'max-age=%s' % self.lifetime

        # resize master picture if necessary
        if targetSize != picture.size:
            picture = ImageOps.fit(picture, targetSize, Image.ANTIALIAS)

        # transfert picture content in response
        save_as = ext
        if ext == "jpg":
            save_as = "JPEG"
        picture.save(resp, save_as)

        if self.saveThumbnail:
            f = ContentFile(resp.content)
            self.storage.save(filename, f)

        return resp
