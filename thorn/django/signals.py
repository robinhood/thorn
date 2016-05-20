"""

    thorn.django.signals
    ====================

    Django model signal utilities.

"""
from __future__ import absolute_import, unicode_literals

from operator import attrgetter
from six import iteritems as items

from celery.utils.imports import symbol_by_name

__all__ = [
    'signal_dispatcher',
    'dispatch_on_create', 'dispatch_on_change', 'dispatch_on_delete',
]


class signal_dispatcher(object):
    signals = None
    use_transitions = False

    def __init__(self, fun, **kwargs):
        self.fun = fun
        self.signals = self.load_signals(self.setup_signals())

    def setup_signals(self):
        return {}

    def load_signals(self, signals):
        return {
            symbol_by_name(sig): handler
            for sig, handler in items(signals)
        }

    def should_dispatch(self, instance, **kwargs):
        return True

    def __call__(self, instance, **kwargs):
        if self.should_dispatch(instance, **kwargs):
            return self.fun(instance, **kwargs)

    def connect(self, sender=None, weak=False, **kwargs):
        [self._connect_signal(signal, handler, sender, weak, **kwargs)
         for signal, handler in items(self.signals)]

    def _connect_signal(self, signal, handler, sender, weak, **kwargs):
        signal.connect(
            handler,
            sender=self.prepare_sender(sender),
            weak=weak,
            **kwargs)

    def prepare_sender(self, sender):
        return sender


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
            instance._previous_version = sender.objects.get(pk=instance.pk)

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
