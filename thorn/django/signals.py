"""Django signal dispatchers."""
from __future__ import absolute_import, unicode_literals

from operator import attrgetter

from django.core.exceptions import ObjectDoesNotExist

from thorn.generic.signals import signal_dispatcher

from .utils import serialize_model

__all__ = [
    'dispatch_on_create',
    'dispatch_on_change',
    'dispatch_on_delete',
    'dispatch_on_m2m_add',
    'dispatch_on_m2m_remove',
    'dispatch_on_m2m_clear',
]


class dispatch_on_create(signal_dispatcher):

    def setup_signals(self):
        return {'django.db.models.signals.post_save': self}

    def should_dispatch(self, instance, raw=False, created=False, **kwargs):
        return not raw and created


class dispatch_on_change(signal_dispatcher):

    def setup_signals(self):
        return {
            'django.db.models.signals.pre_save': self.on_pre_save,
            'django.db.models.signals.post_save': self,
        }

    def on_pre_save(self, instance, sender, raw=False, **kwargs):
        if self.use_transitions and not raw and instance.pk:
            try:
                instance._previous_version = sender.objects.get(pk=instance.pk)
            except ObjectDoesNotExist:
                pass

    def should_dispatch(self, instance, created=False, raw=False, **kwargs):
        return not raw and not created


class dispatch_on_delete(signal_dispatcher):

    def setup_signals(self):
        return {'django.db.models.signals.post_delete': self}


class dispatch_on_m2m_change(signal_dispatcher):

    def __init__(self, fun, related_field, **kwargs):
        super(dispatch_on_m2m_change, self).__init__(fun, **kwargs)
        self.related_field = related_field
        self.actions = self.setup_actions()

    def setup_actions(self):
        return {}

    def setup_signals(self):
        return {'django.db.models.signals.m2m_changed': self.on_m2m_change}

    def prepare_sender(self, sender):
        return attrgetter(self.related_field)(sender).through

    def context(self, instance, model, pk_set, **kwargs):
        return {
            'instance': instance.pk,
            'model': serialize_model(model),
            'pk_set': list(sorted(pk_set or [])),
        }

    def on_m2m_change(self, sender, action, instance, model, **kwargs):
        try:
            handler = self.actions[action]
        except KeyError:
            pass
        else:
            handler(instance, sender=sender, model=model, **kwargs)


class dispatch_on_m2m_add(dispatch_on_m2m_change):

    def setup_actions(self):
        return {'post_add': self}


class dispatch_on_m2m_remove(dispatch_on_m2m_change):

    def setup_actions(self):
        return {'post_remove': self}


class dispatch_on_m2m_clear(dispatch_on_m2m_change):

    def setup_actions(self):
        return {'post_clear': self}
