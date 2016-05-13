from __future__ import absolute_import, unicode_literals

from .case import Case


class test_modules(Case):

    def test_admin(self):
        import thorn.django.admin  # noqa

    def test_apps(self):
        import thorn.django.apps  # noqa

    def test_rest_framework_urls(self):
        import thorn.django.rest_framework.urls  # noqa
