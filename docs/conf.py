# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os

from sphinx_celery import conf

globals().update(conf.build_config(
    'thorn', __file__,
    project='Thorn',
    # version_dev='2.0',
    # version_stable='1.4',
    canonical_url='http://thorn.readthedocs.io',
    webdomain='robinhood.com',
    github_project='robinhood/thorn',
    copyright='2016',
    html_logo='images/logo.png',
    html_favicon='images/favicon.ico',
    extra_extensions=[
        'celery.contrib.sphinx',
    ],
    include_intersphinx={'python', 'sphinx', 'django', 'celery'},
    extra_intersphinx_mapping={
        'requests': ('http://requests.readthedocs.org/en/latest/', None),
    },
    html_prepend_sidebars=['sidebargithub.html'],
    django_settings='testproj.settings',
    path_additions=[os.path.join(os.pardir, 'testproj')],
    apicheck_package='thorn',
    apicheck_ignore_modules=[
        'thorn.django',
        'thorn.django.admin',
        'thorn.django.apps',
        'thorn.django.tasks',
        'thorn.django.rest_framework',
        'thorn.utils',
        'thorn.utils.django.*',
        'thorn.django.migrations.*',
        'thorn.funtests',
        'thorn.funtests.celery',
        'thorn._state',
    ],
))

html_theme = 'thorn'
html_theme_path = ['_theme']


def configcheck_project_settings():
    from thorn.conf import all_settings
    return all_settings()
