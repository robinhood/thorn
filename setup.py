#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

from setuptools.command.test import test as TestCommand  # noqa

import os
import re
import sys
import codecs

if sys.version_info < (2, 7):
    raise Exception('thorn requires Python 2.7 or higher.')

PY3 = sys.version_info[0] >= 3

NAME = 'thorn'
entrypoints = {}
extra = {}

# -*- Classifiers -*-

classes = """
    Development Status :: 4 - Beta
    Programming Language :: Python
    Programming Language :: Python :: 2
    Programming Language :: Python :: 2.7
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.4
    Programming Language :: Python :: 3.5
    Framework :: Django :: 1.8
    Framework :: Django :: 1.9
    License :: OSI Approved :: BSD License
    Intended Audience :: Developers
    Operating System :: OS Independent
"""
classifiers = [s.strip() for s in classes.split('\n') if s]

# -*- Distribution Meta -*-

re_meta = re.compile(r'__(\w+?)__\s*=\s*(.*)')
re_doc = re.compile(r'^"""(.+?)"""')


def add_default(m):
    attr_name, attr_value = m.groups()
    return ((attr_name, attr_value.strip("\"'")), )


def add_doc(m):
    return (('doc', m.groups()[0]), )

pats = {re_meta: add_default, re_doc: add_doc}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'thorn', '__init__.py')) as meta_fh:
    meta = {}
    for line in meta_fh:
        if line.strip() == '# -eof meta-':
            break
        for pattern, handler in pats.items():
            m = pattern.match(line.strip())
            if m:
                meta.update(handler(m))

# -*- Installation Requires -*-

py_version = sys.version_info
is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')


def strip_comments(l):
    return l.split('#', 1)[0].strip()


def reqs(f):
    return list(filter(None, [strip_comments(l) for l in open(
        os.path.join(os.getcwd(), 'requirements', f)).readlines()]))

install_requires = reqs('default.txt')
if not PY3:
    install_requires.extend(reqs('py2.txt'))

# -*- Tests Requires -*-

tests_require = reqs('test.txt') + reqs('test_django.txt')

# -*- Long Description -*-

if os.path.exists('README.rst'):
    long_description = codecs.open('README.rst', 'r', 'utf-8').read()
else:
    long_description = 'See http://pypi.python.org/pypi/thorn/'

# -*- Entry Points -*- #

# -*- %%% -*-


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.pytest_args))

setuptools.setup(
    name=NAME,
    version=meta['version'],
    description=meta['doc'],
    author=meta['author'],
    author_email=meta['contact'],
    url=meta['homepage'],
    platforms=['any'],
    license='BSD',
    packages=setuptools.find_packages(exclude=['ez_setup', 't', 't.*']),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    classifiers=classifiers,
    entry_points=entrypoints,
    long_description=long_description,
    cmdclass={'test': PyTest},
    **extra)
