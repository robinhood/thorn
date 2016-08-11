from __future__ import absolute_import, unicode_literals

from case import Mock

from thorn.reverse import model_reverser


def test_model_reverser():
    app = Mock(name='app')
    instance = Mock(name='instance')
    x = model_reverser('view-name', 'uuid', 'x.y.z', kw1='a', kw2='a.b.c')
    assert x(instance, app=app) is app.reverse.return_value
    app.reverse.assert_called_with(
        'view-name',
        args=[instance.uuid, instance.x.y.z],
        kwargs={'kw1': instance.a, 'kw2': instance.a.b.c},
    )
