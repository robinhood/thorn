from __future__ import absolute_import, unicode_literals

import os


def setup():
    print('-------------- TESTING TESTING TESTING')
    import hashlib
    print('HASHLIB: %r' % (hashlib,))
    print('ALGOS: %r' % (hashlib.algorithms_available,))
    try:
        os.environ['DJANGO_SETTINGS_MODULE']
    except KeyError:
        raise RuntimeError("Use: setup.py test or testproj/manage.py test")
