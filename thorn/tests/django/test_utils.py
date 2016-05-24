from __future__ import absolute_import, unicode_literals

from thorn.django.utils import serialize_model, deserialize_model

from testapp.models import Article

from thorn.tests.case import Case, Mock, patch


class test_deserialize_model(Case):

    def setup(self):
        self.Model = Mock(name='Model')
        self.Model._meta.app_label = 'app_label'
        self.Model._meta.model_name = 'model_name'

    def test_serialize(self):
        self.assertDictEqual(serialize_model(self.Model), {
            'app_label': self.Model._meta.app_label,
            'model_name': self.Model._meta.model_name,
        })

    @patch('thorn.django.utils.apps')
    def test_deserialize(self, django_apps):
        self.assertIs(
            deserialize_model(serialize_model(self.Model)),
            django_apps.get_model.return_value,
        )
        django_apps.get_model.assert_called_with(
            self.Model._meta.app_label,
            self.Model._meta.model_name,
        )

    def test_deserialize__functional_from_class(self):
        self.assertIs(deserialize_model(serialize_model(Article)), Article)

    def test_deserialize__functional_from_instance(self):
        instance = Article(title='foo')
        self.assertIs(deserialize_model(serialize_model(instance)), Article)

    def test_deserialize__already_model(self):
        self.assertIs(deserialize_model(Article), Article)
