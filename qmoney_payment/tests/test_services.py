import os
from django.test import TestCase

from qmoney_payment.models.qmoney_payment import QMoneyPayment
from qmoney_payment.models.policy import get_policy_model, status_to_string
from qmoney_payment.services import create_premium_for

from . import policy_helpers
from . import premium_helpers
from .helpers import Struct


class TestServices(TestCase):

    @classmethod
    def is_standalone_django_app_tests(cls):
        return 'PYTEST_CURRENT_TEST' in os.environ

    @classmethod
    def setUpClass(cls):
        if cls.is_standalone_django_app_tests():
            policy_helpers.setup_policy_table()
            premium_helpers.setup_premium_table()

    @classmethod
    def tearDownClass(cls):
        if cls.is_standalone_django_app_tests():
            premium_helpers.teardown_premium_table()
            policy_helpers.teardown_policy_table()

    def get_one_policy_and_its_old_status(self):
        if self.is_standalone_django_app_tests():
            return get_policy_model().objects.create(
                status=get_policy_model().STATUS_IDLE), None
        policy = get_policy_model().objects.first()
        old_status = policy.status
        policy.status = get_policy_model().STATUS_IDLE
        policy.save()
        return policy, old_status

    def cleanup_one_policy(self):
        if self.is_standalone_django_app_tests():
            self._one_policy.delete()
        self._one_policy.status = self._one_policy_old_status
        self._one_policy.save()

    def setUp(self):
        self._one_policy, self._one_policy_old_status = self.get_one_policy_and_its_old_status(
        )

    def tearDown(self):
        self.cleanup_one_policy()

    def test_aborting_creation_of_premium_when_qmoney_payment_not_yet_proceeded(
            self):
        amount = 1
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            status=QMoneyPayment.Status.W)

        user = Struct(id_for_audit='1')
        assert (
            False,
            'The Qmoney Payment has not been proceeded') == create_premium_for(
                one_qmoney_payment, user)

    def test_creating_premium(self):
        amount = 1 if self.is_standalone_django_app_tests(
        ) else self._one_policy.value
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            status=QMoneyPayment.Status.P)

        user = Struct(id_for_audit='1')

        ok, premium = create_premium_for(one_qmoney_payment, user)

        self._one_policy.refresh_from_db()
        one_qmoney_payment.refresh_from_db()

        assert ok
        assert premium.amount == one_qmoney_payment.amount
        assert self._one_policy == premium.policy
        assert premium.policy.uuid == one_qmoney_payment.policy.uuid
        assert premium.receipt == one_qmoney_payment.uuid
        assert premium.pay_type == 'M'

        assert self._one_policy.status == get_policy_model(
        ).STATUS_ACTIVE, f'Policy should be active but it is {status_to_string(self._one_policy.status)}'

        assert one_qmoney_payment.premium is not None, f'Premium should be set but is not'
        assert one_qmoney_payment.premium == premium, f'Premium should be set but it is not the right one {one_qmoney_payment.premium.uuid} vs {premium.uuid}'

        premium.delete()
