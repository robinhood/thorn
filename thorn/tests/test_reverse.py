from __future__ import absolute_import, unicode_literals

from thorn.reverse import model_reverser

from .case import Case, Mock


class test_model_reverser(Case):

    def test_reverse(self):
        app = Mock(name='app')
        instance = Mock(name='instance')
        x = model_reverser('view-name', 'uuid', 'x.y.z', kw1='a', kw2='a.b.c')
        self.assertIs(x(instance, app=app), app.reverse.return_value)
        app.reverse.assert_called_with(
            'view-name',
            args=[instance.uuid, instance.x.y.z],
            kwargs={'kw1': instance.a, 'kw2': instance.a.b.c},
        )
