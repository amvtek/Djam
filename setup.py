# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='Djam',
    version='0.9.0.dev0',
    author='AmvTek developers',
    author_email='devel@amvtek.com',
    packages=find_packages(),
    url='https://github.com/amvtek/Djam/',
    license='MIT',
    description='Extends Django to work with sqlalchemy and make it behave like Flask',
    long_description=open('README.rst').read(),
)
