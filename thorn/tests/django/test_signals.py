from __future__ import absolute_import, unicode_literals

from thorn.django import signals

from thorn.tests.case import Mock, SignalCase


class test_signal_dispatcher(SignalCase):

    def test_setup_signals(self):
        x = signals.signal_dispatcher(Mock())
        self.assertDictEqual(x.setup_signals(), {})


class SignalDispatcherCase(SignalCase):
    dispatcher = None

    def setup(self):
        self.fun = Mock(name='fun')
        self.dispatch = self.dispatcher(self.fun)
        self.instance = Mock(name='instance')


class test_dispatch_on_create(SignalDispatcherCase):
    dispatcher = signals.dispatch_on_create

    def test_dispatch__when_created(self):
        self.dispatch(self.instance, raw=False, created=True)
        self.fun.assert_called_with(self.instance, raw=False, created=True)

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
        self.fun.assert_called_with(self.instance, raw=False, created=False)

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
        self.dispatch(self.instance, arg=1)
        self.fun.assert_called_with(self.instance, arg=1)

    def test_connect(self):
        self.dispatch.connect(sender=self.Model)
        self.post_delete.connect.assert_called_with(
            self.dispatch, sender=self.Model, weak=False,
        )
