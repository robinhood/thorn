from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock

from django.core.exceptions import ObjectDoesNotExist

from thorn.django import signals
from thorn.django.utils import serialize_model


@pytest.mark.usefixtures('signals')
def test_signal_dispatcher():
    x = signals.signal_dispatcher(Mock())
    assert x.setup_signals() == {}


class SignalDispatcherCase:
    dispatcher = None
    dispatcher_args = ()

    @pytest.fixture(autouse=True)
    def setup_self(self, signals):
        self.signals = signals
        self.Model = Mock(name='Model')
        self.fun = Mock(name='fun')
        self.dispatch = self.dispatcher(self.fun, *self.dispatcher_args)
        self.instance = Mock(name='instance')
        self.related_model = Mock(name='related_model')
        self.related_model._meta.app_label = 'app_label'
        self.related_model._meta.model_name = 'model_name'


class test_dispatch_on_create(SignalDispatcherCase):
    dispatcher = signals.dispatch_on_create

    def test_dispatch__when_created(self):
        self.dispatch(self.instance, raw=False, created=True)
        self.fun.assert_called_with(
            self.instance,
            context={'instance': self.instance.pk},
        )

    def test_dispatch__when_not_created(self):
        self.dispatch(self.instance, raw=False, created=False)
        self.fun.assert_not_called()

    def test_dispatch__when_raw(self):
        self.dispatch(self.instance, raw=True, created=True)
        self.fun.assert_not_called()

    def test_connect(self):
        self.dispatch.connect(sender=self.Model)
        self.signals.post_save.connect.assert_called_with(
            self.dispatch, sender=self.Model, weak=False,
        )


class test_dispatch_on_change(SignalDispatcherCase):
    dispatcher = signals.dispatch_on_change

    def test_dispatch__when_created(self):
        self.dispatch(self.instance, raw=False, created=True)
        self.fun.assert_not_called()

    def test_dispatch__when_not_created(self):
        self.dispatch(self.instance, raw=False, created=False)
        self.fun.assert_called_with(
            self.instance,
            context={'instance': self.instance.pk},
        )

    def test_dispatch__when_raw(self):
        self.dispatch(self.instance, raw=True, created=True)
        self.fun.assert_not_called()

    def test_on_pre_save(self):
        self.dispatch.use_transitions = True
        instance = Mock(Name='instance')
        sender = Mock(name='sender')
        self.dispatch.on_pre_save(instance, sender, raw=False)
        sender.objects.get.assert_called_once_with(pk=instance.pk)
        assert instance._previous_version is sender.objects.get()

    def test_on_pre_save__ObjectDoesNotExist(self):
        self.dispatch.use_transitions = True
        instance = Mock(Name='instance')
        instance._previous_version = None
        sender = Mock(name='sender')
        sender.objects.get.side_effect = ObjectDoesNotExist()
        self.dispatch.on_pre_save(instance, sender, raw=False)
        sender.objects.get.assert_called_once_with(pk=instance.pk)
        assert instance._previous_version is None

    def test_on_pre_save__disabled(self):
        self.dispatch.use_transitions = False
        instance = Mock(name='instance')
        sender = Mock(name='sender')
        self.dispatch.on_pre_save(instance, sender, raw=False)
        sender.objects.get.assert_not_called()

    def test_on_pre_save__disabled_on_raw(self):
        self.dispatch.use_transitions = True
        instance = Mock(Name='instance')
        sender = Mock(name='sender')
        self.dispatch.on_pre_save(instance, sender, raw=True)
        sender.objects.get.assert_not_called()

    def test_on_pre_save__disabled_on_object_creation(self):
        self.dispatch.use_transitions = True
        instance = Mock(Name='instance')
        instance.pk = None
        sender = Mock(name='sender')
        self.dispatch.on_pre_save(instance, sender, raw=False)
        sender.objects.get.assert_not_called()

    def test_connect(self):
        self.dispatch.connect(sender=self.Model)
        self.signals.post_save.connect.assert_called_with(
            self.dispatch, sender=self.Model, weak=False,
        )


class test_dispatch_on_delete(SignalDispatcherCase):
    dispatcher = signals.dispatch_on_delete

    def test_dispatch(self):
        self.dispatch(self.instance)
        self.fun.assert_called_with(
            self.instance, context={'instance': self.instance.pk})

    def test_connect(self):
        self.dispatch.connect(sender=self.Model)
        self.signals.post_delete.connect.assert_called_with(
            self.dispatch, sender=self.Model, weak=False,
        )


def test_dispatch_on_m2m_change_interface():
    x = signals.dispatch_on_m2m_change(Mock(), Mock())
    assert x.setup_actions() == {}


@pytest.mark.parametrize('Dispatcher', [
    signals.dispatch_on_m2m_add,
    signals.dispatch_on_m2m_remove,
    signals.dispatch_on_m2m_clear,
])
class test_dispatch_on_m2m_change(SignalDispatcherCase):
    dispatcher = Mock()
    dispatcher_args = ('tags.sgat',)

    def test_dispatch(self, Dispatcher):
        dispatch = Dispatcher(self.fun, *self.dispatcher_args)
        self.instance = Mock(name='instance')
        dispatch(
            self.instance, pk_set={31, 123}, model=self.related_model,
        )
        self.fun.assert_called_with(self.instance, context={
            'instance': self.instance.pk,
            'model': serialize_model(self.related_model),
            'pk_set': [31, 123],
        })

    def test_connect(self, Dispatcher):
        dispatch = Dispatcher(self.fun, *self.dispatcher_args)
        dispatch.connect(sender=self.Model)
        self.signals.m2m_changed.connect.assert_called_with(
            dispatch.on_m2m_change,
            sender=self.Model.tags.sgat.through, weak=False,
        )

    def test_on_m2m_change__post_add(self, Dispatcher):
        dispatch = Dispatcher(self.fun, *self.dispatcher_args)
        handler = dispatch.actions['post_add'] = Mock(name='post_add')
        dispatch.on_m2m_change(
            sender=self.Model, action='post_add', instance=self.instance,
            model=self.Model, foo=1,
        )
        handler.assert_called_with(
            self.instance, sender=self.Model, model=self.Model, foo=1,
        )

    def test_on_m2m_change__no_handler(self, Dispatcher):
        dispatch = Dispatcher(self.fun, *self.dispatcher_args)
        dispatch.on_m2m_change(
            sender=self.Model, action='foo',
            instance=self.instance, model=self.Model,
        )
