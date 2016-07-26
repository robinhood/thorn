"""Django-related utilities."""
from __future__ import absolute_import, unicode_literals

from collections import Mapping

from django.apps import apps

__all__ = ['serialize_model', 'deserialize_model']


def serialize_model(m):
    return {'app_label': m._meta.app_label, 'model_name': m._meta.model_name}


def deserialize_model(m):
    if isinstance(m, Mapping):
        return apps.get_model(m['app_label'], m['model_name'])
    return m
