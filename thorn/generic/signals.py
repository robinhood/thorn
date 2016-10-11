"""Dispatching by signal."""
from __future__ import absolute_import, unicode_literals

from six import iteritems as items

from celery.utils.imports import symbol_by_name

__all__ = ['signal_dispatcher']


class signal_dispatcher(object):
    """Signal dispatcher abstraction."""

    signals = None

    def __init__(self, fun, use_transitions=False, **kwargs):
        self.fun = fun
        self.use_transitions = use_transitions
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
            return self.fun(
                instance, context=self.context(instance, **kwargs))

    def connect(self, sender=None, weak=False, **kwargs):
        [self._connect_signal(signal, handler, sender, weak, **kwargs)
         for signal, handler in items(self.signals)]

    def _connect_signal(self, signal, handler, sender, weak, **kwargs):
        signal.connect(
            handler,
            sender=self.prepare_sender(sender),
            weak=weak,
            **kwargs)

    def context(self, instance, **kwargs):
        return {'instance': instance.pk}

    def prepare_sender(self, sender):
        return sender
