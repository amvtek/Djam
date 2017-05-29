# -*- coding: utf-8 -*-
"""
    djam.mailutils
    ~~~~~~~~~~~~~~

    Export EmailTemplate class that simplifies integrating email messaging to a
    Django application

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

import re
import string
from email.mime.image import MIMEImage

import django
from django.template.loader import get_template
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.encoding import force_text, force_bytes
from django.utils import translation

# overcome deprecation of Context in django 1.8+
if django.VERSION >= (1, 8, 0):
    Context = dict
else:
    from django.template import Context

class InlineImage(MIMEImage):
    """
    A MIMEImage suitable for 'cid' embedding
    """

    def __init__(self, name, binary):
        MIMEImage.__init__(self, force_bytes(binary))
        self.add_header('Content-ID', "<{}>".format(name))

class EmailTemplate(object):
    """
    A class that allows to construct multi-alternatives email with text part
    and optional html part. Internationalization of the email maybe handled by
    the django i18n middleware or directly by setting explicitely a language
    parameter.

    Example :
    ---------

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
    
    Parameters
    ----------
    subjectTpl : str or lazy_gettext...
     string template (using $ variable substitution ) defining email
     subject.

    textTpl : str
     path to django text template
     shall always be defined even if an html template is also provided

    htmlTpl : optional str
     path to django html template

    toAddresses : optional List[email]
     default list of destinary
     when message is rendered, this list may be overwritten

    fromAddress : optional email
     default sender address
     when message is rendered, this address may be overwritten

    fromUser : optional str or lazy_gettext
     default sender name (maybe internationalized)
     when message is rendered, this name may be overwritten
    
    replyToAddress : optional email
     set message reply to address
     when message is rendered, this address may be overwritten

    lang : optional str
     allows forcing email language to another than what HTTP request provides.
     This is usefull when sending notification messages

    docAttachments : optional List[(name, bytes, mimetype) or callable]
     callable allows templating message attachment (eg pdf invoice generation).
     They accept any number of keywords arguments.

    inlineImages : optional List[(name, bytes) or callable]
     inlines can be referenced in the html part of the message using img tag
     with "cid:name" source...
     callable allows templating inline image (eg barcode generation).
     They accept any number of keywords arguments and return (name, bytes)
     tuple.
    """

    STR_TPL_REGEX = re.compile(r"\$")

    def __init__(
            self, subjectTpl, textTpl,
            htmlTpl=None, toAddresses=None, fromAddress=None,
            fromUser=None, replyToAddress=None, lang=None,
            docAttachments=None, inlineImages=None):

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
        
        # preload inline images if any
        if inlineImages:
            inlines = []
            for inline in inlineImages:
                if callable(inline):
                    inlines.append(inline)
                else:
                    inlines.append(InlineImage(*inline))
            inlineImages = inlines
        self.inlineImages = inlineImages

        self.lang = lang  # freeze email language code, usefull for admin...

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
            subject = force_text(subject)
            if self.STR_TPL_REGEX.search(subject):
                subject = self.render_param(subject, cacheSubjectTpl, kwargs)

            # Update fromAddress if fromUser is set
            if fromUser is not None:
                # if ugettext_lazy was used, this shall translate it
                fromUser = force_text(fromUser)
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

            # Add html alternative
            if self.htmlTpl:
                htmlPart = self.htmlTpl.render(ctx)
                msg.attach_alternative(htmlPart, "text/html")
            
            # add inline images
            if self.inlineImages:
                
                if self.htmlTpl:
                    msg.mixed_subtype = 'related'

                for inline in self.inlineImages:

                    if callable(inline):
                        # inline callable shall return a 2-tuple containing
                        # inline_name, inline_bytes
                        inline = InlineImage(*inline(**kwargs))
                    
                    msg.attach(inline)

            # add file attachments
            # those shows as attached documents in msg...
            if self.docAttachments:
                for attachment in self.docAttachments:

                    if callable(attachment):
                        # attachment callable shall return a 3-tuple containing
                        # attachment_name, attachment_bytes, attachment_mime_type
                        attachment = attachment(**kwargs)
                    
                    msg.attach(*attachment)

            return msg

        finally:
            if savedLang:
                translation.activate(savedLang)
