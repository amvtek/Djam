# -*- coding: utf-8 -*-
"""
    djam._django_to_sqlalchemy
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Contains equivalents for names of databases configuration parameters in
    between django and sqlalchemy.

    This is work in progress...

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

# Provide correspondance in between django and sqlalchemy for database
# config variables... 
_PARAMS = [
    ("NAME", "database"), ("ENGINE", "drivername"), ("HOST", "host"),
    ("PORT", "port"), ("USER", "username"), ("PASSWORD", "password")
]


# Map django.backend to sqlalchemy drivername, fill free to improve this
_DJ2SA = {
    "django.db.backends.postgresql_psycopg2": "postgresql+psycopg2",
    "django.contrib.gis.db.backends.postgis": "postgresql+psycopg2",
    "django.db.backends.mysql": "mysql+mysqldb",
    "django.db.backends.oracle": "oracle+cx_oracle",
    "django.db.backends.sqlite3": "sqlite"
}

