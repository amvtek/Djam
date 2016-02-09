####
DJAM
####

Djam (a short for Django amalgamation...) is a reusable Django application that
extends Django in various way :

1. sqlalchemy ORM integration
2. Base Form class that simplifies working with the sqlalchemy ORM 
3. global request object
4. class based view that works like middleware stack  
5. email templates
6. middleware that allows fine grained control over `CORS`_ authorizations

Some of those components have been inspired by the `Flask`_ and `WTForms`_ frameworks.

.. _Flask: http://flask.pocoo.org/
.. _WTForms: https://wtforms.readthedocs.org/en/latest/
.. _CORS: https://www.w3.org/TR/cors/
