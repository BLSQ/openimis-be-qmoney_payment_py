import collections
import os
import time
import uuid
import unittest

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import RequestFactory, TestCase
from django.utils.module_loading import import_string

import graphene
from graphene.test import Client

from simplegmail import Gmail

from qmoney_payment.models.qmoney_payment import QMoneyPayment
from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model
from qmoney_payment.schema import Query, Mutation

from . import qmoney_helpers
from .helpers import gmail_wait_and_get_recent_emails_with_qmoney_otp, current_datetime, extract_otp_from_email_messages, gmail_mark_messages_as_read, gmail_mark_as_read_recent_emails_with_qmoney_otp
from .helpers import Struct, random_string
from .helpers import is_standalone_django_app_tests
from .fake_policy import FakePolicy
from .fake_premium import FakePremium
from .fake_mutation_log import FakeMutationLog
from .fakemodel_helpers import setup_table_for, teardown_table_for


def site_root():
    if callable(settings.SITE_ROOT):
        # it is a function in the main app
        return settings.SITE_ROOT()

    return settings.SITE_ROOT


class TestQMoneyPaymentGraphQL(TestCase):

    DEFAULT_POLICY_VALUE = 1

    @classmethod
    def gmail_client(cls):
        if 'RUN_ALSO_TESTS_WITH_GMAIL' not in os.environ:
            return None
        client = Gmail()
        time.sleep(5)
        gmail_mark_as_read_recent_emails_with_qmoney_otp(client)
        return client

    @classmethod
    def gql_client(cls):
        schema = graphene.Schema(query=Query, mutation=Mutation)
        return Client(schema)

    @classmethod
    def request_context(cls):
        context = RequestFactory().post(f'/{site_root()}graphql')
        context.user = cls._admin_user
        return context

    @classmethod
    def setUpClass(cls):
        cls._qmoney_payer = qmoney_helpers.qmoney_payer()
        cls._gql_client = TestQMoneyPaymentGraphQL.gql_client()
        if is_standalone_django_app_tests():
            setup_table_for(FakeMutationLog)
            setup_table_for(FakePolicy)
            setup_table_for(FakePremium)
        cls._gmail_client = cls.gmail_client()
        cls._anonymous_user = AnonymousUser()
        cls._admin_user = cls.create_admin_user()
        cls._guest_user = cls.create_user_without_rights()

    @classmethod
    def tearDownClass(cls):
        if is_standalone_django_app_tests():
            teardown_table_for(FakePremium)
            teardown_table_for(FakePolicy)
            teardown_table_for(FakeMutationLog)
        if 'RUN_ALSO_TESTS_WITH_GMAIL' in os.environ:
            gmail_mark_as_read_recent_emails_with_qmoney_otp(cls._gmail_client)
        if not is_standalone_django_app_tests():
            cls._admin_user.delete()
            cls._guest_user.delete()

    @classmethod
    def create_admin_user(cls):
        username = f'TQPGQL_Admin-{random_string(4)}'

        if is_standalone_django_app_tests():
            return Struct(username=username,
                          id_for_audit='1',
                          id=1,
                          has_perms=lambda list: True)

        create_test_interactive_user = import_string(
            'core.test_helpers.create_test_interactive_user')
        return create_test_interactive_user(username=username)

    @classmethod
    def create_user_without_rights(cls):
        username = f'TQPGQL_Guest-{random_string(4)}'
        if is_standalone_django_app_tests():
            return Struct(username=username,
                          id_for_audit='2',
                          id=666,
                          has_perms=lambda list: False)

        create_test_interactive_user = import_string(
            'core.test_helpers.create_test_interactive_user')
        return create_test_interactive_user(username=username, roles=[1])

    def execute_gql_with_context(self, query):
        return self._gql_client.execute(query,
                                        context_value=self._request_context)

    def switch_to_user(self, user):
        self._request_context.user = user

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
        self._request_context = self.request_context()

    def tearDown(self):
        self.cleanup_one_policy()

    def get_none_or_lower(self, item, key):
        if item.get(key) is None:
            return None
        return item.get(key).lower()

    def generate_expected(self, item=None):
        if item is None:
            return {'data': {'qmoneyPayment': None}}

        return {
            'data': {
                'qmoneyPayment': {
                    'amount': item.get('amount', 0),
                    'premiumUuid':
                    self.get_none_or_lower(item, 'premium_uuid'),
                    'externalTransactionId': item.get('transaction_id', None),
                    'payerWallet': item['payer_wallet'],
                    'policyUuid': self.get_none_or_lower(item, 'policy_uuid'),
                    'status': item.get('status', 'INITIATED'),
                    'uuid': item['uuid']
                }
            }
        }

    def generate_expected_list(self, items=[]):
        return {
            'data': {
                'qmoneyPayments': {
                    'edges': [{
                        'node': {
                            'amount':
                            item.get('amount', 0),
                            'premiumUuid':
                            self.get_none_or_lower(item, 'premium_uuid'),
                            'externalTransactionId':
                            None,
                            'payerWallet':
                            item['payer_wallet'],
                            'policyUuid':
                            self.get_none_or_lower(item, 'policy_uuid'),
                            'status':
                            item.get('status', 'INITIATED'),
                            'uuid':
                            item['uuid']
                        }
                    } for item in items]
                }
            }
        }

    def test_failing_at_listing_all_qmoney_payments_with_unauthorized_user(
            self):
        self.switch_to_user(self._anonymous_user)
        query = '''
        query {
          qmoneyPayments{
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        '''

        actual = self.execute_gql_with_context(query)
        assert actual['data']['qmoneyPayments'] is None
        assert actual['errors'][0][
            'message'] == "['User needs to be authenticated for this operation']"

        self.switch_to_user(self._guest_user)
        actual = self.execute_gql_with_context(query)
        assert actual['data']['qmoneyPayments'] is None
        assert actual['errors'][0][
            'message'] == 'User not authorized for this operation'

    def test_listing_qmoney_payments_for_a_given_policy_when_there_is_none(
            self):
        query = '''
        query {
          qmoneyPayments(policyUuid: "%s"){
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (self._one_policy.uuid, )

        expected = self.generate_expected_list()

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_when_there_is_none(self):
        query = '''
        query {
          qmoneyPayments{
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        '''

        expected = self.generate_expected_list()

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_when_there_is_one(self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            amount=amount, payer_wallet=self._qmoney_payer)

        query = '''
        query {
          qmoneyPayments{
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        '''

        expected = self.generate_expected_list([{
            'uuid':
            f'{one_qmoney_payment.uuid}',
            'amount':
            amount,
            'payer_wallet':
            self._qmoney_payer,
        }])

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_for_a_given_policy_when_there_is_one(
            self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer)

        query = '''
        query {
          qmoneyPayments(policyUuid: "%s"){
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (self._one_policy.uuid, )

        expected = self.generate_expected_list([{
            'uuid':
            f'{one_qmoney_payment.uuid}',
            'policy_uuid':
            f'{self._one_policy.uuid}',
            'amount':
            amount,
            'payer_wallet':
            self._qmoney_payer,
        }])

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

        query = '''
        query {
          qmoneyPayments(policyUuid: "%s"){
            edges{
              node{
                uuid
                status
                amount
                payerWallet
                policyUuid
                premiumUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (uuid.uuid4(), )

        expected = self.generate_expected_list()

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_failing_at_retrieving_one_existing_qmoney_payment_with_unauthorized_user(
            self):
        self.switch_to_user(self._anonymous_user)

        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer)

        query = '''
        query {
          qmoneyPayment(uuid: "%s"){
            uuid
            status
            amount
            payerWallet
            policyUuid
            premiumUuid
            externalTransactionId
          }
        }
        ''' % (one_qmoney_payment.uuid, )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['qmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == "['User needs to be authenticated for this operation']"

        self.switch_to_user(self._guest_user)
        actual = self.execute_gql_with_context(query)
        assert actual['data']['qmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'User not authorized for this operation'

    def test_retrieving_one_existing_qmoney_payment_with_its_uuid(self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer)

        query = '''
        query {
          qmoneyPayment(uuid: "%s"){
            uuid
            status
            amount
            payerWallet
            policyUuid
            premiumUuid
            externalTransactionId
          }
        }
        ''' % (one_qmoney_payment.uuid, )

        expected = self.generate_expected({
            'uuid': f'{one_qmoney_payment.uuid}',
            'policy_uuid': f'{self._one_policy.uuid}',
            'amount': amount,
            'payer_wallet': self._qmoney_payer,
        })

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

        query = '''
        query {
          qmoneyPayment(uuid: "%s"){
            uuid
            status
            amount
            payerWallet
            policyUuid
            premiumUuid
            externalTransactionId
          }
        }
        ''' % (uuid.uuid4(), )

        expected = self.generate_expected()

        actual = self.execute_gql_with_context(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def generate_expected_mutation_ok_response(self, mutation_name, item=None):
        result = self.generate_expected(item)['data']
        result['ok'] = True
        return {'data': collections.OrderedDict({mutation_name: result})}

    def test_failing_at_requesting_qmoney_payment_for_an_existing_given_policy_with_unauthorized_user(
            self):
        self.switch_to_user(self._anonymous_user)
        amount = 10
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == "['User needs to be authenticated for this operation']"

        self.switch_to_user(self._guest_user)
        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'User not authorized for this operation'

    def test_requesting_qmoney_payment_for_an_existing_given_policy(self):
        amount = 10
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data'][
            'requestQmoneyPayment'], f'should have returned a `requestQmoneyPayment`, but got {actual}'
        assert 'ok' in actual['data']['requestQmoneyPayment'] and actual[
            'data']['requestQmoneyPayment'][
                'ok'], f'should have returned ok, but got {actual}'
        assert actual['data']['requestQmoneyPayment']['qmoneyPayment'][
            'uuid'] is not None
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['uuid'],
                'policy_uuid':
                f'{self._one_policy.uuid}',
                'status':
                'WAITING_FOR_CONFIRMATION',
                'amount':
                amount,
                'payer_wallet':
                self._qmoney_payer,
                'transaction_id':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['externalTransactionId']
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        mutation_log = FakeMutationLog.objects.all().first()

        assert mutation_log.client_mutation_label == f'Request QMoney Payment (wallet: {self._qmoney_payer}, amount: {amount}, policy: {self._one_policy.uuid})'
        assert mutation_log.status == FakeMutationLog.SUCCESS

    def test_canceling_an_existing_qmoney_payment(self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer)

        query = '''
        mutation {
          cancelQmoneyPayment(uuid: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (one_qmoney_payment.uuid)

        actual = self.execute_gql_with_context(query)
        assert 'data' in actual and actual['data'][
            'cancelQmoneyPayment'], f'should have returned a `cancelQmoneyPayment`, but got {actual}'
        assert 'ok' in actual['data']['cancelQmoneyPayment'] and actual[
            'data']['cancelQmoneyPayment'][
                'ok'], f'should have returned ok, but got {actual}'
        assert actual['data']['cancelQmoneyPayment']['qmoneyPayment'][
            'uuid'] is not None
        expected = self.generate_expected_mutation_ok_response(
            'cancelQmoneyPayment', {
                'uuid':
                actual['data']['cancelQmoneyPayment']['qmoneyPayment']['uuid'],
                'policy_uuid':
                f'{self._one_policy.uuid}',
                'status':
                'CANCELED',
                'amount':
                amount,
                'payer_wallet':
                self._qmoney_payer
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        mutation_log = FakeMutationLog.objects.all().first()

        assert mutation_log.client_mutation_label == f'Cancel QMoney Payment ({one_qmoney_payment.uuid})'
        assert mutation_log.status == FakeMutationLog.SUCCESS

    def test_failing_at_canceling_an_existing_proceeded_qmoney_payment(self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer,
            status=QMoneyPayment.Status.P)

        query = '''
        mutation {
          cancelQmoneyPayment(uuid: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (one_qmoney_payment.uuid)

        actual = self.execute_gql_with_context(query)
        assert actual['data']['cancelQmoneyPayment'] is None
        expected_error_message = 'Something went wrong. The payment could not be canceled. The transaction is PROCEEDED. Reason: The payment cannot be canceled as it has already been proceeded.'
        assert actual['errors'][0]['message'] == expected_error_message

        mutation_log = FakeMutationLog.objects.all().first()
        assert mutation_log.client_mutation_label == f'Cancel QMoney Payment ({one_qmoney_payment.uuid})'
        assert mutation_log.status == FakeMutationLog.ERROR
        assert mutation_log.error == expected_error_message

    def test_failing_at_canceling_an_non_existing_qmoney_payment(self):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=self._one_policy,
            amount=amount,
            payer_wallet=self._qmoney_payer)
        false_uuid = uuid.uuid4()

        query = '''
        mutation {
          cancelQmoneyPayment(uuid: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (false_uuid)

        actual = self.execute_gql_with_context(query)
        assert actual['data']['cancelQmoneyPayment'] is None
        expected_error_message = 'The UUID does not correspond to any recorded QMoney payment.'
        assert actual['errors'][0]['message'] == expected_error_message

        mutation_log = FakeMutationLog.objects.all().first()
        assert mutation_log.client_mutation_label == f'Cancel QMoney Payment ({false_uuid})'
        assert mutation_log.status == FakeMutationLog.ERROR
        assert mutation_log.error == expected_error_message

    def test_failing_at_requesting_a_2nd_qmoney_payment_for_an_existing_given_policy(
            self):
        amount = 10
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data'][
            'requestQmoneyPayment'], f'should have returned a `requestQmoneyPayment`, but got {actual}'
        assert 'ok' in actual['data']['requestQmoneyPayment'] and actual[
            'data']['requestQmoneyPayment'][
                'ok'], f'should have returned ok, but got {actual}'
        assert actual['data']['requestQmoneyPayment']['qmoneyPayment'][
            'uuid'] is not None
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['uuid'],
                'policy_uuid':
                f'{self._one_policy.uuid}',
                'status':
                'WAITING_FOR_CONFIRMATION',
                'amount':
                amount,
                'payer_wallet':
                self._qmoney_payer,
                'transaction_id':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['externalTransactionId']
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        mutation_log = FakeMutationLog.objects.all().first()

        assert mutation_log.client_mutation_label == f'Request QMoney Payment (wallet: {self._qmoney_payer}, amount: {amount}, policy: {self._one_policy.uuid})'
        assert mutation_log.status == FakeMutationLog.SUCCESS

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'The number of ongoing unproceeded transactions have already reached the maximum allowed 1. Please proceed or cancel existing ones before requesting new payment.'

    def test_failing_at_requesting_qmoney_payment_for_an_existing_given_non_idle_policy(
            self):
        self._one_policy.status = get_policy_model().STATUS_ACTIVE
        self._one_policy.save()
        amount = 10
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is None
        expected_error_message = f'Something went wrong. The payment could not be requested. The transaction is INITIATED. Reason: The Policy {self._one_policy.uuid} should be Idle but it is not.'
        assert actual['errors'][0]['message'] == expected_error_message

        mutation_log = FakeMutationLog.objects.all().first()

        assert mutation_log.client_mutation_label == f'Request QMoney Payment (wallet: {self._qmoney_payer}, amount: {amount}, policy: {self._one_policy.uuid})'
        assert mutation_log.status == FakeMutationLog.ERROR
        assert mutation_log.error == expected_error_message

    def test_failing_at_requesting_qmoney_payment_for_an_absent_given_policy(
            self):
        policy_uuid = uuid.uuid4()
        amount = 0
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            policy_uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is None

        expected_error_message = 'The UUID does not correspond to any existing policy.'
        assert actual['errors'][0]['message'] == expected_error_message

        mutation_log = FakeMutationLog.objects.all().first()

        assert mutation_log.client_mutation_label == f'Request QMoney Payment (wallet: {self._qmoney_payer}, amount: {amount}, policy: {policy_uuid})'
        assert mutation_log.status == FakeMutationLog.ERROR
        assert mutation_log.error == expected_error_message

    def test_failing_at_requesting_qmoney_payment_without_policy(self):
        query = '''
        mutation {
          requestQmoneyPayment() {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        '''

        actual = self.execute_gql_with_context(query)
        assert 'Syntax Error GraphQL (3:32) Expected Name' in actual['errors'][
            0]['message']

    @unittest.skipIf('RUN_ALSO_TESTS_WITH_GMAIL' not in os.environ,
                     'Skipping tests using Gmail')
    def test_requesting_and_proceeding_qmoney_payment_for_an_existing_given_policy(
            self):
        amount = self.DEFAULT_POLICY_VALUE
        before_initiating_transaction = current_datetime()

        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              premiumUuid
              policyUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'][
            'ok'], 'should have returned ok'
        uuid = actual['data']['requestQmoneyPayment']['qmoneyPayment']['uuid']
        assert uuid is not None
        transaction_id = actual['data']['requestQmoneyPayment'][
            'qmoneyPayment']['externalTransactionId']
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid': uuid,
                'policy_uuid': f'{self._one_policy.uuid}',
                'status': 'WAITING_FOR_CONFIRMATION',
                'amount': amount,
                'payer_wallet': self._qmoney_payer,
                'transaction_id': transaction_id,
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            self._gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        query = '''
        mutation {
          proceedQmoneyPayment(uuid: "%s", otp: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            uuid,
            otp,
        )

        actual = self.execute_gql_with_context(query)
        premium = get_premium_model().objects.filter(
            policy__uuid=self._one_policy.uuid, receipt=uuid).first()
        assert premium != None
        self._one_policy.refresh_from_db()
        assert self._one_policy.status == get_policy_model().STATUS_ACTIVE
        expected = self.generate_expected_mutation_ok_response(
            'proceedQmoneyPayment', {
                'uuid': uuid,
                'policy_uuid': f'{self._one_policy.uuid}',
                'status': 'PROCEEDED',
                'amount': amount,
                'payer_wallet': self._qmoney_payer,
                'transaction_id': transaction_id,
                'premium_uuid': premium.uuid
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        mutation_log = FakeMutationLog.objects.filter(
            client_mutation_label__icontains='Proceed').first()

        assert mutation_log.client_mutation_label == f'Proceed QMoney Payment ({uuid}, otp: {otp})'
        assert mutation_log.status == FakeMutationLog.SUCCESS

        premium.delete()

    @unittest.skipIf('RUN_ALSO_TESTS_WITH_GMAIL' not in os.environ,
                     'Skipping tests using Gmail')
    def test_failing_at_proceeding_qmoney_payment_for_an_existing_given_policy_with_unauthorized_user(
            self):
        amount = self.DEFAULT_POLICY_VALUE
        before_initiating_transaction = current_datetime()

        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              premiumUuid
              policyUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            self._one_policy.uuid,
            amount,
            self._qmoney_payer,
        )

        actual = self.execute_gql_with_context(query)
        assert actual['data']['requestQmoneyPayment'] is not None
        assert actual['data']['requestQmoneyPayment'][
            'ok'], 'should have returned ok'
        uuid = actual['data']['requestQmoneyPayment']['qmoneyPayment']['uuid']
        assert uuid is not None
        transaction_id = actual['data']['requestQmoneyPayment'][
            'qmoneyPayment']['externalTransactionId']
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid': uuid,
                'policy_uuid': f'{self._one_policy.uuid}',
                'status': 'WAITING_FOR_CONFIRMATION',
                'amount': amount,
                'payer_wallet': self._qmoney_payer,
                'transaction_id': transaction_id,
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            self._gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        query = '''
        mutation {
          proceedQmoneyPayment(uuid: "%s", otp: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              premiumUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            uuid,
            otp,
        )

        self.switch_to_user(self._anonymous_user)
        actual = self.execute_gql_with_context(query)
        assert actual['data']['proceedQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == "['User needs to be authenticated for this operation']"

        self.switch_to_user(self._guest_user)
        actual = self.execute_gql_with_context(query)
        assert actual['data']['proceedQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'User not authorized for this operation'
