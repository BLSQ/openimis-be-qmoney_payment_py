import os

from django.apps import apps
from django.test import TestCase

from .helpers import is_standalone_django_app_tests

from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model


class TestCustomModels(TestCase):

    def test_loading_fake_policy_model(self):
        model = get_policy_model()
        assert model.__name__ == 'FakePolicy' if is_standalone_django_app_tests(
        ) else 'Policy'

    def test_raising_exception_if_none_policy_model_provided(self):
        with self.settings(CUSTOM_MODELS=None):
            try:
                model = get_policy_model()
                if is_standalone_django_app_tests():
                    assert False, f'Loading the custom Policy model should have failed but it did not. We got {model}'
                else:
                    assert True
            except Exception as error:
                if is_standalone_django_app_tests():
                    assert str(
                        error
                    ) == 'A custom model for Policy has not been set up. Please provide one in settings.'
                else:
                    assert False, 'Loading the custom Policy model should succeed as it loads the one from the contributions module in the context of the OpenIMIS app.'

    def test_loading_fake_premium_model(self):
        model = get_premium_model()
        assert model.__name__ == 'FakePremium' if is_standalone_django_app_tests(
        ) else 'Premium'

    def test_raising_exception_if_none_premium_model_provided(self):
        with self.settings(CUSTOM_MODELS=None):
            try:
                model = get_premium_model()
                if is_standalone_django_app_tests():
                    assert False, f'Loading the custom Premium model should have failed but it did not. We got {model}'
                else:
                    assert True
            except Exception as error:
                if is_standalone_django_app_tests():
                    assert str(
                        error
                    ) == 'A custom model for Premium has not been set up. Please provide one in settings.'
                else:
                    assert False, 'Loading the custom Premium model should succeed as it loads the one from the contributions module in the context of the OpenIMIS app.'
