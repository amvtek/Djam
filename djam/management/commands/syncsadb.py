# -*- coding: utf-8 -*-
"""
    djam.management.commands.syncsadb
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Allow to synchronize changes in a set of sqlalchemy Metadata with selected
    database.

    :email: devel@amvtek.com
"""
from __future__ import unicode_literals

from optparse import make_option
import inspect

from django.db import DEFAULT_DB_ALIAS
from django.db.models import get_apps
from django.core.management.base import NoArgsCommand

from sqlalchemy import MetaData

from djam.sqlalchemy import Schema, get_engine


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (

        make_option(
            '--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS,
            help="Nominate a database to synchronize. " \
                 "Defaults to the 'default' database."),

        make_option(
            '--schema', action='store', dest='schema',
            help="Nominate a schema to synchronize. " \
                 "If not set all schemas will be synchronized, except if " \
                 "they are bound to another database than current..."
        )
    )

    help = "Create the database tables for all sqlalchemy schemas(metadata) " \
           "that can be found in INSTALLED_APPS models modules...\n" \
           "Note that only non existing tables will be created."

    def handle_noargs(self, **options):

        # retrieve sqlalchemy engine for selected database
        db = options.get('database')
        engine = get_engine(db)

        # retrieve schema
        schema = options.get('schema')
        if schema is not None:
            schema = Schema(schema) # account for setting overwrite if any

        metadatas = set([])
        for modelmodul in get_apps():

            for n, m in inspect.getmembers(modelmodul):

                if isinstance(m, MetaData):

                    # if o is bound to another db than engine, ignore it
                    if (m.bind is not None) and m.bind != engine:
                        continue

                    # if a schema was set
                    # ignore metadata that don't belong to it
                    if schema and m.schema != schema:
                        continue

                    metadatas.add(m)

        for metadata in metadatas:
            print("now synchronizing %s" % metadata)
            metadata.create_all(bind=engine)
