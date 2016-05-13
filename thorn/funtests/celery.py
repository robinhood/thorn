"""

    thorn.funtests.celery
    =====================

    Celery application used for the Thorn Cyanide test suite.

"""
from __future__ import absolute_import, unicode_literals

import cyanide.app
import django
import os
import sys
import thorn

dist = os.path.join(
    os.path.abspath(os.path.dirname(thorn.__file__)),
    os.pardir,
)
sys.path.append(os.path.join(dist, 'testproj'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproj.settings_funtests')
django.setup()

app = cyanide.app.App(set_as_current=False)
app.cyanide_suite = 'thorn.funtests.suite:Default'
app.conf.CELERY_IMPORTS = [
    'thorn.tasks',
    'thorn.funtests.tasks',
    'cyanide.tasks',
]
