# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='Djam',
    version='0.8.1',
    author='AmvTek developers',
    author_email='devel@amvtek.com',
    packages=['djam'],
    url='https://github.com/amvtek/Djam/',
    license='MIT',
    description='Extends Django to work with sqlalchemy and make it behave like Flask',
    long_description=open('README.rst').read(),
)