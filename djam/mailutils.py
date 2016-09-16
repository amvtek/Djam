# -*- coding: utf-8 -*-
"""
    djam.mailutils
    ~~~~~~~~~~~~~~

    Export EmailTemplate class that simplifies integrating email messaging to a
    Django application

    :copyright: (c) 2010 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

import re
import string

from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils import translation


class EmailTemplate(object):
    """
    A class that allows to construct multi-alternatives email with text part
    and optional html part. Internationalization of the email maybe handled by
    the django i18n middleware or directly by setting explicitely a language
    parameter.

    example of use:
    ---------------

    WelcomeEmail = EmailTemplate(
                        subjectTpl = _("Welcome $fname $lname"),
                        fromUser = _("$fname $lname via $serviceName"),
                        textTpl = "emails/welcome.txt",
                        htmlTpl = "emails/welcome.html"
                        )
    where:
    ------
        * subjectTpl : simple string template prepared using lazy_gettext
        * fromUser   : simple string template prepared using lazy_gettext
        * textTpl    : path to django text template
        * htmlTpl    : path to django html template

    ...later on

    msg = WelcomeEmail(["user@example.com"],fname="test",lname="user")
    ...
    msg.send()
    """

    STR_TPL_REGEX = re.compile(r"\$")

    def __init__(
            self, subjectTpl, textTpl,
            htmlTpl=None, toAddresses=None, fromAddress=None,
            fromUser=None, replyToAddress=None, docAttachments=None,
            lang=None):

        self.subjectTpl = subjectTpl  # expected to be ugettext_lazy processed...
        self.fromUser = fromUser  # expected to be ugettext_lazy processed...

        self.paramTplCache = {}

        self.textTpl = get_template(textTpl)

        if htmlTpl:
            self.htmlTpl = get_template(htmlTpl)
            self.msg_factory = EmailMultiAlternatives
        else:
            self.htmlTpl = None
            self.msg_factory = EmailMessage

        self.toAddresses = toAddresses
        self.fromAddress = fromAddress
        self.replyToAddress = replyToAddress
        self.docAttachments = docAttachments
        self.lang = None  # freeze email language code, usefull for admin...

    def render_param(self, paramTplString, cacheable, kwargs):

        if cacheable:
            cache = self.paramTplCache  # local alias
            paramTpl = cache.get(paramTplString)
            if paramTpl is None:
                paramTpl = string.Template(paramTplString)
                cache[paramTplString] = paramTpl
        else:
            paramTpl = string.Template(paramTplString)

        return paramTpl.substitute(kwargs)

    def __call__(self, toAddresses=None, fromAddress=None, fromUser=None,
                 replyToAddress=None, subject=None, lang=None, **kwargs):

        toAddresses = toAddresses or self.toAddresses
        if not toAddresses:
            raise ValueError("missing destinaries toAddresses list")

        fromAddress = fromAddress or self.fromAddress
        if not fromAddress:
            raise ValueError("missing originator address")

        cacheSubjectTpl = (subject is None)
        subject = subject or self.subjectTpl
        if not subject:
            raise ValueError("missing email subject")

        cacheFromUserTpl = (fromUser is None)
        fromUser = fromUser or self.fromUser

        replyToAddress = replyToAddress or self.replyToAddress

        savedLang = None
        try:

            # Control i18n if lang is explicitely set
            lang = lang or self.lang
            if lang is not None:
                curLang = translation.get_language()
                if lang != curLang:
                    translation.activate(lang)
                    savedLang = curLang

            # Render title
            # if ugettext_lazy was used, this shall translate it
            subject = unicode(subject)
            if self.STR_TPL_REGEX.search(subject):
                subject = self.render_param(subject, cacheSubjectTpl, kwargs)

            # Update fromAddress if fromUser is set
            if fromUser is not None:
                # if ugettext_lazy was used, this shall translate it
                fromUser = unicode(fromUser)
                if self.STR_TPL_REGEX.search(fromUser):
                    fromUser = self.render_param(
                        fromUser, cacheFromUserTpl, kwargs
                    )
                fromAddress = "%s <%s>" % (fromUser, fromAddress)

            # Instantiate template context
            ctx = Context(kwargs)

            # Render the plain text part
            body = self.textTpl.render(ctx)

            # prepare headers dict
            hdrs = {}
            if replyToAddress:
                hdrs["Reply-To"] = replyToAddress
            #
            hdrs = hdrs or None

            # Construct msg
            msg = self.msg_factory(
                subject=subject, body=body, from_email=fromAddress,
                to=toAddresses, headers=hdrs
            )

            # add file attachments
            # those shows as attached documents in msg...
            if self.docAttachments:
                for attachment in self.docAttachments:
                    # attachment callable shall return a 3-tuple containing
                    # attachment_name, attachment_bytes, attachment_mime_type
                    msg.attach(*attachment(**kwargs))

            # Add html alternative
            if self.htmlTpl:
                htmlPart = self.htmlTpl.render(ctx)
                msg.attach_alternative(htmlPart, "text/html")

            return msg

        finally:
            if savedLang:
                translation.activate(savedLang)
