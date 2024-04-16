import collections
import os
import time
import uuid
import unittest

from django.db import connection
from django.test import TestCase

import graphene
from graphene.test import Client

from simplegmail import Gmail

from qmoney_payment.models.qmoney_payment import QMoneyPayment
from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model
from qmoney_payment.schema import Query, Mutation

from . import policy_helpers
from . import premium_helpers
from . import qmoney_helpers
from .helpers import gmail_wait_and_get_recent_emails_with_qmoney_otp, current_datetime, extract_otp_from_email_messages, gmail_mark_messages_as_read, gmail_mark_as_read_recent_emails_with_qmoney_otp


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
    def is_standalone_django_app_tests(cls):
        return 'PYTEST_CURRENT_TEST' in os.environ

    @classmethod
    def setUpClass(cls):
        cls._qmoney_payer = qmoney_helpers.qmoney_payer()
        cls._gql_client = TestQMoneyPaymentGraphQL.gql_client()
        if cls.is_standalone_django_app_tests():
            policy_helpers.setup_policy_table()
            premium_helpers.setup_premium_table()
        cls._gmail_client = cls.gmail_client()

    @classmethod
    def tearDownClass(cls):
        if cls.is_standalone_django_app_tests():
            premium_helpers.teardown_premium_table()
            policy_helpers.teardown_policy_table()
        if 'RUN_ALSO_TESTS_WITH_GMAIL' in os.environ:
            gmail_mark_as_read_recent_emails_with_qmoney_otp(cls._gmail_client)

    def get_one_policy_and_its_previous_state(self):
        if self.is_standalone_django_app_tests():
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
        if self.is_standalone_django_app_tests():
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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def generate_expected_mutation_ok_response(self, mutation_name, item=None):
        result = self.generate_expected(item)['data']
        result['ok'] = True
        return {'data': collections.OrderedDict({mutation_name: result})}

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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == f'Something went wrong. The payment could not be requested. The transaction is INITIATED. Reason: The Policy {self._one_policy.uuid} should be Idle but it is not.'

    def test_failing_at_requesting_qmoney_payment_for_an_absent_given_policy(
            self):
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
            uuid.uuid4(),
            0,
            self._qmoney_payer,
        )

        actual = self._gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'The UUID does not correspond to any existing policy.'

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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
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

        actual = self._gql_client.execute(query)
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
        premium.delete()
