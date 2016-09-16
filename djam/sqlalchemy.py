# -*- coding: utf-8 -*-
"""
    djam.sqlalchemy
    ~~~~~~~~~~~~~~~

    Provide utilities that eases using sqlalchemy in a django project

    :copyright: (c) 2014 by sc AmvTek srl
    :email: devel@amvtek.com
"""
from __future__ import unicode_literals, absolute_import

import threading

from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.url import URL

from django.conf import settings

from .utils import SettingRename
from ._django_to_sqlalchemy import _DJ2SA, _PARAMS

__all__ = ['Session', 'SqlAlchemyMiddleware', 'object_session', 'get_db_session', 'get_engine']

# ============================================================================
# Configure database Session class

Session = getattr(settings, 'SQLALCHEMY_SESSION', None)
if Session is None:
    Session = scoped_session(sessionmaker())
if not isinstance(Session, ScopedSession):
    Session = scoped_session(Session)

object_session = Session.object_session

# ============================================================================
# SqlAlchemyMiddleware shall be activated for sqlalchemy Session to be properly
# disposed at the end of each request

class SqlAlchemyMiddleware(object):
    """
    dispose sqlalchemy Session at the end of each request
    """

    def process_response(self, request, response):
        "dispose sqlalchemy session..."

        Session.remove()
        return response

    def process_exception(self, request, exception):
        "dispose sqlalchemy session..."

        Session.remove()

# ============================================================================
# Schema object allow databases schema names to be changed using settings
# module. It is usefull when defining sqlalchemy metadata schema.
#    Example :
#      metadata = ...
#      metadata.schema = Schema('public')
#      If later on schema name shall be changed add setting :
#      SCHEMA_PUBLIC = 'something_else'
#      metadata.schema will be 'something_else'...

Schema = SettingRename("SCHEMA_{0}".format)



# ============================================================================
# Registry maintain an index of sqlalchemy engines built using informations
# contained in settings module.
# The Registry index maybe defined directly in the settings module 

class ConfigError(ValueError):
    pass


class Registry(object):
    """
    Maintain an internal index of sqlalchemy engines that corresponds to the
    different databases connections defined in the settings.

    Registry instance provides the following methods :
    --------------------------------------------------

        get_db_session(db='default') which returns a sqlalchemy
        Session bound to named database.

        get_engine(db='default') that returns the sqlalchemy Engine that
        correspond to named database.

        get_connection(db='default') that returns a sqlalchemy Connection to
        the named database.


    The Registry may be configured in 2 ways :
    ------------------------------------------

        1. By explicitely defining setting SQLALCHEMY_ENGINES that is expected
        to be a dictionary of {"dbname":sqlalchemy_engine}

        2. Or alternatively by 'translating' to sqlalchemy the database
        configuration informations that are contained in setting DATABASES.
        Note that:
            1. Some sqlalchemy specific configuration maybe added directly to
            database configuration dictionary in DATABASES by prefixing key
            with 'sqlalchemy.'.
            2. If a database configuration dictionary contains
            {..."sqlalchemy.ignored" : True } no engine will be created for the
            corresponding database.
    """

    # Use the 'Borg pattern' to share state between all instances.
    # See source code of django.db.models.loading for example...
    __shared_state = dict(

        # mapping of dbname to configured sqlalchemy engine
        _engineIdx={},

        # everything below here is used only when populating _engineIdx
        _loaded=False,
        _wLock=threading.RLock(),
    )

    def __init__(self):

        self.__dict__ = self.__shared_state
        self._populate()

    def get_db_session(self, db='default'):
        "return sqlalchemy Session bound to db"

        s = Session()
        s.bind = self._engineIdx[db]
        return s

    def get_engine(self, db='default'):
        "return sqlalchemy Engine that was configured for db"

        return self._engineIdx[db]

    def _populate(self):
        """
        populates internal _engineIdx making use of django settings
          If settings defines SQLALCHEMY_ENGINES we have our index.
          Otherwise we use informations in DATABASES to configure one
          sqlalchemy engine for each settings database...
        """

        # do not continue if _engineIdx was already loaded
        if self._loaded:
            return

        # lock to prevent concurrent _populate ...
        self._wLock.acquire()

        try:

            if self._loaded:
                return

            # check settings to see if SQLALCHEMY_ENGINES dict has been set
            engineIdx = getattr(settings, 'SQLALCHEMY_ENGINES', None)
            if engineIdx is not None:

                # we check that every value in engineIdx are Engine instance
                for v in engineIdx.values():
                    if not isinstance(v, Engine):
                        raise ConfigError("Invalid SQLALCHEMY_ENGINES setting")

                self._engineIdx = engineIdx

            else:

                # we attend to make use of DATABASES settings finding
                # equivalent for django databases configuration...
                databases = settings.DATABASES

                saprefix = "sqlalchemy.{0}".format
                engineIdx = {}

                for dbkey, config in databases.items():

                    # skip if sqlalchemy.ignored is True
                    if config.get('sqlalchemy.ignored'):
                        continue

                    # at this stage saconfig is expected to contains upper case django
                    # configuration variable eg ENGINE, HOST,... and prospectively some
                    # sqlalchemy related config variables prefixed by 'sqlalchemy.'
                    saconfig = dict(config)

                    if saconfig.get('sqlalchemy.url') is None:

                        urlparams = {}

                        # reuse django database configuration 
                        # for missing sqlalchemy config variables
                        for djkey, sakey in _PARAMS:
                            saconf = saconfig.pop(saprefix(sakey), None)
                            urlparams[sakey] = saconf or saconfig.get(djkey) or None

                        # translate django ENGINE to sqlalchemy drivername 
                        ename = urlparams['drivername']
                        urlparams['drivername'] = _DJ2SA.get(ename, ename)

                        saconfig['sqlalchemy.url'] = URL(**urlparams)

                    # create sqlalchemy engine from saconfig parameters...
                    engineIdx[dbkey] = engine_from_config(saconfig)

                self._engineIdx = engineIdx

            self._loaded = True

        finally:

            self._wLock.release()

# Construct Registry instance to export get_db_session , get_engine 
_registry = Registry()
get_db_session = _registry.get_db_session
get_engine = _registry.get_engine

# ============================================================================
# minimal Permission system
# CreatePermissionMeta can be used with declarative_base to create Permission
# objects on models...


class Permission(object):
    def __init__(self, name):
        self.name = name

    _reprFmt = "<Permission {0} at {1:#x}>".format

    def __repr__(self):
        return self._reprFmt(self.name, id(self))


class CreatePermissionMeta(DeclarativeMeta):
    """
    Custom DeclarativeMeta that add Permissions to generated model class.
    Permissions to be added are listed in _permissions attribute
    declared on model...
    """


    def __init__(cls, classname, bases, dico):

        super(CreatePermissionMeta, cls).__init__(classname, bases, dico)

        permissions = set([])

        # add Permission to model class if _permissions defined
        toBeCreatedPermissions = getattr(cls, '_permissions', None)
        if toBeCreatedPermissions is not None:
            for permName in toBeCreatedPermissions:
                perm = Permission("%s.%s" % (classname, permName))
                setattr(cls, permName, perm)
                permissions.add(perm)
        cls.registeredPermissions = permissions


class RoleMap(object):
    """
    I define which permissions are part of a role...
    """

    def __init__(self):
        self.__rolePerm = {}

    def register(self, role, *permOrModels):
        """
        Add a set of permissions to a role...
        """

        rolePermissions = self.__rolePerm.setdefault(role, set([]))
        for obj in permOrModels:
            if isinstance(obj, Permission):
                rolePermissions.add(obj)
            else:
                permissions = getattr(obj, 'registeredPermissions', [])
                for perm in permissions:
                    rolePermissions.add(perm)
