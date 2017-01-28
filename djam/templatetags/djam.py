# -*- coding: utf-8 -*-
"""
    djam.templatetags.djam
    ~~~~~~~~~~~~~~~~~~~~~~

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

from django import template
from django.core.urlresolvers import reverse

from ..thumbnailer import build_thumbnail_path

register = template.Library()

@register.simple_tag(takes_context=True)
def thumbnail(context, mpath, width, height=None):
    "return thumbnail url for mpath & dimensions..."

    # retrieve thumbnailer_view name from context...
    thumbnailer_view = context.get("thumbnailer_view", "thumbnailer")

    # calculates thumbnail path
    thumbpath = build_thumbnail_path(mpath, width, height)

    return reverse(thumbnailer_view, args=(thumbpath,))
