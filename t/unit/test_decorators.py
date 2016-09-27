from __future__ import absolute_import, unicode_literals

import pytest

from case import ANY, Mock

from thorn.decorators import webhook_model
from thorn.events import ModelEvent

from testapp import models


@pytest.mark.django_db()
@pytest.mark.usefixtures('reset_signals')
@pytest.mark.usefixtures('transactional_db')
class test_functional_webhook_model:

    def setup(self):
        self.Model = models.Foo
        assert not hasattr(self.Model, 'webhooks')
        self.obj, _ = self.Model.objects.get_or_create(username='elaine')

    def teardown_method(self, method):
        models.Foo.webhooks = None
        delattr(models.Foo, 'webhooks')

    def test_is_dict(self):
        Model = webhook_model(on_change=ModelEvent('x.y'))(self.Model)
        assert (Model.webhooks['on_change'] is
                Model.webhooks.events['on_change'])

    def test_on_change(self):
        on_change = ModelEvent('x.change')
        Model = webhook_model(
            on_change=on_change,
            sender_field='username',
        )(self.Model)
        assert Model.webhooks.events['on_change'] is on_change
        on_change.send = Mock(name='event.send')
        self.obj.username = 'jerry'
        self.obj.save()
        on_change.send.assert_called_with(
            instance=self.obj,
            data=self.obj.webhooks.payload(self.obj),
            headers=None,
            sender=self.obj.username,
            context={'instance': self.obj.pk},
        )

    def test_on_create(self):
        on_create = ModelEvent('x.create')
        Model = webhook_model(on_create=on_create)(self.Model)
        assert Model.webhooks.events['on_create'] is on_create
        on_create.send = Mock(name='event.send')
        self.Model.objects.filter(username='cosmo').delete()
        obj, _ = self.Model.objects.get_or_create(username='cosmo')
        on_create.send.assert_called_with(
            instance=obj,
            data=obj.webhooks.payload(obj),
            headers=None,
            sender=None,
            context={'instance': obj.pk},
        )

    def test_on_delete(self):
        on_delete = ModelEvent('x.delete')
        Model = webhook_model(on_delete=on_delete)(self.Model)
        assert Model.webhooks.events['on_delete'] is on_delete
        on_delete.send = Mock(name='event.send')
        obj_pk = self.obj.pk
        self.obj.delete()
        on_delete.send.assert_called_with(
            instance=self.obj,
            data=self.obj.webhooks.payload(self.obj),
            headers=None,
            sender=None,
            context={'instance': obj_pk},
        )

    def test_on_custom_with_filter_dispatching_on_delete(self):
        jerry, _ = self.Model.objects.get_or_create(username='jerry')
        on_jerry_delete = ModelEvent(
            'x.delete', username__eq='jerry').dispatches_on_delete()
        Model = webhook_model(on_jerry_delete=on_jerry_delete)(self.Model)
        assert (Model.webhooks.events['on_jerry_delete'] is
                on_jerry_delete)
        on_jerry_delete.send = Mock(name='event.send')
        self.obj.delete()
        on_jerry_delete.send.assert_not_called()

        jerry_pk = jerry.pk
        jerry.delete()

        on_jerry_delete.send.assert_called_with(
            instance=jerry,
            data=jerry.webhooks.payload(jerry),
            headers=None,
            sender=None,
            context={'instance': jerry_pk},
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
            data=obj2.webhooks.payload(obj2),
            headers=None,
            sender=None,
            context={'instance': obj2.pk},
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
        assert on_create.reverse is reverse
        assert on_change.reverse is reverse2

    def test_dict_compat(self):
        on_create = ModelEvent('x.create')
        self.Model = webhook_model(
            on_create=on_create)(self.Model)
        assert self.Model.webhooks['on_create'] is on_create
        self.Model.webhooks['on_create'] = 42
        assert self.Model.webhooks['on_create'] == 42
        del(self.Model.webhooks['on_create'])
        with pytest.raises(KeyError):
            self.Model.webhooks['on_create']


class test_webhook_model:

    def test_with_on_create__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_create = ModelEvent('x.create')

        signals.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_change__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_change = ModelEvent('x.change')

        signals.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_delete__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_delete = ModelEvent('x.delete')

        signals.post_delete.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_delete__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_custom = ModelEvent('x.delete').dispatches_on_delete()

        signals.post_delete.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_change__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_custom = ModelEvent('x.change').dispatches_on_change()

        signals.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_on_custom_create__connects(self, signals):

        @webhook_model
        class Model(object):

            class webhooks:
                on_custom = ModelEvent('x.create').dispatches_on_create()

        signals.post_save.connect.assert_called_with(
            ANY, sender=Model, weak=False,
        )

    def test_with_many_args(self, signals):
        with pytest.raises(TypeError):
            webhook_model('foo', 'foo')

    def test_arg_not_callable(self, signals):
        with pytest.raises(TypeError):
            webhook_model('foo')

    def test_webhooks_not_a_class(self, signals):
        with pytest.raises(TypeError):
            @webhook_model
            class Model(object):
                webhooks = 42
