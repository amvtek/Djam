# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='Djam',
    version='0.9.8',
    author='AmvTek developers',
    author_email='devel@amvtek.com',
    license='MIT',
    packages=find_packages(),
    url='https://github.com/amvtek/Djam/',
    description='Extends Django to work with sqlalchemy and make it behave like Flask',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
