from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock

from thorn.django.utils import serialize_model, deserialize_model

from testapp.models import Article


class test_deserialize_model:

    @pytest.fixture()
    def Model(self):
        m = Mock(name='Model')
        m._meta.app_label = 'app_label'
        m._meta.model_name = 'model_name'
        return m

    def test_serialize(self, Model):
        assert serialize_model(Model) == {
            'app_label': Model._meta.app_label,
            'model_name': Model._meta.model_name,
        }

    def test_deserialize(self, patching, Model):
        django_apps = patching('thorn.django.utils.apps')
        assert (deserialize_model(serialize_model(Model)) is
                django_apps.get_model.return_value)
        django_apps.get_model.assert_called_with(
            Model._meta.app_label,
            Model._meta.model_name,
        )

    def test_deserialize__functional_from_class(self):
        assert deserialize_model(serialize_model(Article)) == Article

    def test_deserialize__functional_from_instance(self):
        instance = Article(title='foo')
        assert deserialize_model(serialize_model(instance)) == Article

    def test_deserialize__already_model(self):
        assert deserialize_model(Article) is Article
