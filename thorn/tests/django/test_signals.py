from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ObjectDoesNotExist

from thorn.django import signals
from thorn.django.utils import serialize_model

from thorn.tests.case import Mock, SignalCase


class test_signal_handler(SignalCase):

    def setup(self):
        self.dispatcher = Mock(name='dispatcher')
        self.sender = Mock(name='sender')
        self.handler = signals.signal_handler(
            self.dispatcher, 1, 2, 3, sender=self.sender, foo=4,
        )

    def test_init(self):
        self.assertIs(self.handler.dispatcher, self.dispatcher)
        self.assertIs(self.handler.sender, self.sender)
        self.assertTupleEqual(self.handler.args, (1, 2, 3))
        self.assertDictEqual(self.handler.kwargs, {'foo': 4})

    def test_call(self):
        fun = Mock(name='fun')
        ret = self.handler(fun)
        self.dispatcher.assert_called_with(fun, 1, 2, 3, foo=4)
        self.dispatcher().connect.assert_called_with(sender=self.sender)
        self.assertIs(ret, fun)


class test_signal_dispatcher(SignalCase):

    def test_setup_signals(self):
        x = signals.signal_dispatcher(Mock())
        self.assertDictEqual(x.setup_signals(), {})


class SignalDispatcherCase(SignalCase):
    dispatcher = None
    dispatcher_args = ()

    def setup(self):
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
        self.post_save.connect.assert_called_with(
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
        self.assertIs(instance._previous_version, sender.objects.get())

    def test_on_pre_save__ObjectDoesNotExist(self):
        self.dispatch.use_transitions = True
        instance = Mock(Name='instance')
        instance._previous_version = None
        sender = Mock(name='sender')
        sender.objects.get.side_effect = ObjectDoesNotExist()
        self.dispatch.on_pre_save(instance, sender, raw=False)
        sender.objects.get.assert_called_once_with(pk=instance.pk)
        self.assertIsNone(instance._previous_version)

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
        self.post_save.connect.assert_called_with(
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
        self.post_delete.connect.assert_called_with(
            self.dispatch, sender=self.Model, weak=False,
        )


class test_dispatch_on_m2m_change(SignalDispatcherCase):
    dispatcher = signals.dispatch_on_m2m_change
    dispatcher_args = ('tags.sgat',)

    def test_dispatch(self):
        self.dispatch(
            self.instance, pk_set={31, 123}, model=self.related_model,
        )
        self.fun.assert_called_with(self.instance, context={
            'instance': self.instance.pk,
            'model': serialize_model(self.related_model),
            'pk_set': [31, 123],
        })

    def test_connect(self):
        self.dispatch.connect(sender=self.Model)
        self.m2m_changed.connect.assert_called_with(
            self.dispatch.on_m2m_change,
            sender=self.Model.tags.sgat.through, weak=False,
        )

    def test_on_m2m_change__post_add(self):
        handler = self.dispatch.actions['post_add'] = Mock(name='post_add')
        self.dispatch.on_m2m_change(
            sender=self.Model, action='post_add', instance=self.instance,
            model=self.Model, foo=1,
        )
        handler.assert_called_with(
            self.instance, sender=self.Model, model=self.Model, foo=1,
        )

    def test_on_m2m_change__no_handler(self):
        self.dispatch.on_m2m_change(
            sender=self.Model, action='foo',
            instance=self.instance, model=self.Model,
        )


class test_dispatch_on_m2m_add(test_dispatch_on_m2m_change):
    dispatcher = signals.dispatch_on_m2m_add


class test_dispatch_on_m2m_remove(test_dispatch_on_m2m_change):
    dispatcher = signals.dispatch_on_m2m_remove


class test_dispatch_on_m2m_clear(test_dispatch_on_m2m_change):
    dispatcher = signals.dispatch_on_m2m_clear
