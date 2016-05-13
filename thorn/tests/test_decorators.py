from __future__ import absolute_import, unicode_literals

from thorn.decorators import webhook_model
from thorn.events import ModelEvent

from testapp import models

from .case import ANY, Mock, RealSignalCase, SignalCase


class test_functional_webhook_model(RealSignalCase):

    def setup(self):
        self.Model = models.Foo
        self.obj, _ = self.Model.objects.get_or_create(username='elaine')

    def teardown(self):
        self.Model.objects.all().delete()

    def test_on_change(self):
        on_change = ModelEvent('x.change')
        Model = webhook_model(
            on_change=on_change,
            sender_field='username',
        )(self.Model)
        self.assertIs(Model.webhook_events.events['on_change'], on_change)
        on_change.send = Mock(name='event.send')
        self.obj.username = 'jerry'
        self.obj.save()
        on_change.send.assert_called_with(
            instance=self.obj,
            data=self.obj.webhook_payload(),
            sender=self.obj.username,
        )

    def test_on_create(self):
        on_create = ModelEvent('x.create')
        Model = webhook_model(on_create=on_create)(self.Model)
        self.assertIs(Model.webhook_events.events['on_create'], on_create)
        on_create.send = Mock(name='event.send')
        self.Model.objects.filter(username='cosmo').delete()
        obj, _ = self.Model.objects.get_or_create(username='cosmo')
        on_create.send.assert_called_with(
            instance=obj,
            data=obj.webhook_payload(),
            sender=None,
        )

    def test_on_delete(self):
        on_delete = ModelEvent('x.delete')
        Model = webhook_model(on_delete=on_delete)(self.Model)
        self.assertIs(Model.webhook_events.events['on_delete'], on_delete)
        on_delete.send = Mock(name='event.send')
        self.obj.delete()
        on_delete.send.assert_called_with(
            instance=self.obj,
            data=self.obj.webhook_payload(),
            sender=None,
        )

    def test_on_custom_with_filter_dispatching_on_delete(self):
        jerry, _ = self.Model.objects.get_or_create(username='jerry')
        on_jerry_delete = ModelEvent(
            'x.delete', username__eq='jerry').dispatches_on_delete()
        Model = webhook_model(on_jerry_delete=on_jerry_delete)(self.Model)
        self.assertIs(
            Model.webhook_events.events['on_jerry_delete'],
            on_jerry_delete,
        )
        on_jerry_delete.send = Mock(name='event.send')
        self.obj.delete()
        on_jerry_delete.send.assert_not_called()

        jerry.delete()

        on_jerry_delete.send.assert_called_with(
            instance=jerry,
            data=jerry.webhook_payload(),
            sender=None,
        )

    def test_on_change__does_not_dispatch_on_create(self):
        on_create = ModelEvent('x.create')
        on_change = ModelEvent('x.change')
        on_create.send = Mock(name='on_create.send')
        on_change.send = Mock(name='on_change.send')

        self.Model = webhook_model(
            on_create=on_create, on_change=on_change)(self.Model)

        obj2, _ = self.Model.objects.get_or_create(username='cosmo')

        on_create.send.assert_called_with(
            instance=obj2,
            data=obj2.webhook_payload(),
            sender=None,
        )
        on_change.send.assert_not_called()

    def test_contribute_to_event__reverse_propagates(self):
        reverse = Mock(name='reverse')
        reverse2 = Mock(name='reverse2')
        on_create = ModelEvent('x.create', reverse=reverse)
        on_change = ModelEvent('x.change')
        self.Model = webhook_model(
            on_create=on_create, on_change=on_change, reverse=reverse2,
        )(self.Model)
        self.assertIs(on_create.reverse, reverse)
        self.assertIs(on_change.reverse, reverse2)


class test_webhook_model(SignalCase):

    def test_with_on_create__connects(self):
        Model = webhook_model(on_create=ModelEvent('x.create'))(self.Model)
        self.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_change__connects(self):
        Model = webhook_model(on_change=ModelEvent('x.change'))(self.Model)
        self.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_delete__connects(self):
        Model = webhook_model(on_delete=ModelEvent('x.delete'))(self.Model)
        self.post_delete.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_delete__connects(self):
        Model = webhook_model(
            on_custom=ModelEvent('x.delete').dispatches_on_delete(),
        )(self.Model)
        self.post_delete.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_change__connects(self):
        Model = webhook_model(
            on_custom=ModelEvent('x.change').dispatches_on_change(),
        )(self.Model)
        self.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_create__connects(self):
        Model = webhook_model(
            on_custom=ModelEvent('x.create').dispatches_on_create(),
        )(self.Model)
        self.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )
