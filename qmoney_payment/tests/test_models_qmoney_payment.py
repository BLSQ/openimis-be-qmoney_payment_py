from django.core.validators import ValidationError
from django.test import TestCase

from qmoney_payment.models.qmoney_payment import QMoneyPayment
from qmoney_payment.models.policy import get_policy_model

from .helpers import is_standalone_django_app_tests
from .fake_policy import FakePolicy
from .fake_premium import FakePremium
from .fakemodel_helpers import setup_table_for, teardown_table_for


class TestQMoneyPaymentGraphQL(TestCase):
    DEFAULT_POLICY_VALUE = 1

    @classmethod
    def setUpClass(cls):
        if is_standalone_django_app_tests():
            setup_table_for(FakePolicy)
            setup_table_for(FakePremium)

    @classmethod
    def tearDownClass(cls):
        if is_standalone_django_app_tests():
            teardown_table_for(FakePremium)
            teardown_table_for(FakePolicy)

    def get_one_policy_and_its_previous_state(self):
        if is_standalone_django_app_tests():
            return get_policy_model().objects.create(
                status=get_policy_model().STATUS_IDLE), None
        policy = get_policy_model().objects.first()
        previous_policy_state = {
            'status': policy.status,
            'value': policy.value
        }
        policy.status = get_policy_model().STATUS_IDLE
        policy.value = self.DEFAULT_POLICY_VALUE
        policy.save()
        return policy, previous_policy_state

    def cleanup_one_policy(self):
        if is_standalone_django_app_tests():
            self._one_policy.delete()
            return
        self._one_policy.status = self._one_policy_previous_state['status']
        self._one_policy.value = self._one_policy_previous_state['value']
        self._one_policy.save()

    def setUp(self):
        self._one_policy, self._one_policy_previous_state = self.get_one_policy_and_its_previous_state(
        )

    def tearDown(self):
        self.cleanup_one_policy()

    def test_failing_at_creating_new_qmoney_payments_when_some_are_still_unproceeded_or_uncancelled(
            self):
        amount = 10
        qmoney_payer = 'abcdef'
        proceeded_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=qmoney_payer,
            status=QMoneyPayment.Status.P)
        cancelled_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=qmoney_payer,
            status=QMoneyPayment.Status.C)
        one_initiated_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy, amount=amount, payer_wallet=qmoney_payer)
        try:
            two_initiated_qmoney_payment = QMoneyPayment.objects.create(
                policy=self._one_policy,
                amount=amount,
                payer_wallet=qmoney_payer)
            assert False, f'It should not be possible to create a new Qmoney Payment as there is already one unproceeded or uncancelled'
        except ValidationError as error:
            assert error.message == 'The number of ongoing unproceeded transactions have already reached the maximum allowed 1. Please proceed or cancel existing ones before requesting new payment.'
