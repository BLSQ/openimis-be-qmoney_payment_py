import collections
import pytest
import uuid

from django.db import connection

import graphene
from graphene.test import Client

from qmoney_payment.models.qmoney_payment import QMoneyPayment
from qmoney_payment.models.policy import Policy
from qmoney_payment.schema import Query, Mutation

import policy_helpers

from helpers import gmail_wait_and_get_recent_emails_with_qmoney_otp, current_datetime, extract_otp_from_email_messages, gmail_mark_messages_as_read


@pytest.mark.django_db()
class TestQMoneyPaymentGraphQL():

    @pytest.fixture(scope='class')
    def gql_client(self):
        schema = graphene.Schema(query=Query, mutation=Mutation)
        return Client(schema)

    @pytest.fixture(scope='function')
    def one_policy(self):
        policy = Policy.objects.create(status=Policy.STATUS_IDLE)
        yield policy
        policy.delete()

    @pytest.fixture(scope='class', autouse=True)
    def setup_policy_table(self, django_db_setup, django_db_blocker):
        with django_db_blocker.unblock():
            policy_helpers.setup_policy_table()
        yield
        with django_db_blocker.unblock():
            policy_helpers.teardown_policy_table()

    # not sure it's necessary, to test
    @pytest.fixture(scope='function', autouse=True)
    def clean_up_qmoney_table(self, django_db_setup):
        yield
        QMoneyPayment.objects.all().delete()

    def generate_expected_mutation_ok_response(self, mutation_name, item=None):
        result = self.generate_expected(item)['data']
        result['ok'] = True
        return {'data': collections.OrderedDict({mutation_name: result})}

    def generate_expected(self, item=None):
        if item is None:
            return {'data': {'qmoneyPayment': None}}

        return {
            'data': {
                'qmoneyPayment': {
                    'amount': item.get('amount', 0),
                    'contributionUuid': None,
                    'externalTransactionId': item.get('transaction_id', None),
                    'payerWallet': item['payer_wallet'],
                    'policyUuid': item.get("policy_uuid"),
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
                            'amount': item.get('amount', 0),
                            'contributionUuid': None,
                            'externalTransactionId': None,
                            'payerWallet': item['payer_wallet'],
                            'policyUuid': item.get('policy_uuid'),
                            'status': item.get('status', 'INITIATED'),
                            'uuid': item['uuid']
                        }
                    } for item in items]
                }
            }
        }

    def test_listing_qmoney_payments_for_a_given_policy_when_there_is_none(
            self, gql_client, one_policy):
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
                contributionUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (one_policy.uuid, )

        expected = self.generate_expected_list()

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_when_there_is_none(self, gql_client):
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
                contributionUuid
                externalTransactionId
              }
            }
          }
        }
        '''

        expected = self.generate_expected_list()

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_when_there_is_one(
            self, gql_client, qmoney_payer):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            amount=amount, payer_wallet=qmoney_payer)

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
                contributionUuid
                externalTransactionId
              }
            }
          }
        }
        '''

        expected = self.generate_expected_list([{
            'uuid': f'{one_qmoney_payment.uuid}',
            'amount': amount,
            'payer_wallet': qmoney_payer,
        }])

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_listing_all_qmoney_payments_for_a_given_policy_when_there_is_one(
            self, gql_client, one_policy, qmoney_payer):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=one_policy, amount=amount, payer_wallet=qmoney_payer)

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
                contributionUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (one_policy.uuid, )

        expected = self.generate_expected_list([{
            'uuid': f'{one_qmoney_payment.uuid}',
            'policy_uuid': f'{one_policy.uuid}',
            'amount': amount,
            'payer_wallet': qmoney_payer,
        }])

        actual = gql_client.execute(query)
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
                contributionUuid
                externalTransactionId
              }
            }
          }
        }
        ''' % (uuid.uuid4(), )

        expected = self.generate_expected_list()

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_retrieving_one_existing_qmoney_payment_with_its_uuid(
            self, gql_client, one_policy, qmoney_payer):
        amount = 10
        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=one_policy, amount=amount, payer_wallet=qmoney_payer)

        query = '''
        query {
          qmoneyPayment(uuid: "%s"){
            uuid
            status
            amount
            payerWallet
            policyUuid
            contributionUuid
            externalTransactionId
          }
        }
        ''' % (one_qmoney_payment.uuid, )

        expected = self.generate_expected({
            'uuid': f'{one_qmoney_payment.uuid}',
            'policy_uuid': f'{one_policy.uuid}',
            'amount': amount,
            'payer_wallet': qmoney_payer,
        })

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

        query = '''
        query {
          qmoneyPayment(uuid: "%s"){
            uuid
            status
            amount
            payerWallet
            policyUuid
            contributionUuid
            externalTransactionId
          }
        }
        ''' % (uuid.uuid4(), )

        expected = self.generate_expected()

        actual = gql_client.execute(query)
        assert expected == actual, f'should have been {expected}, but we got {actual}'

    def test_requesting_qmoney_payment_for_an_existing_given_policy(
            self, gql_client, one_policy, qmoney_payer):
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
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            one_policy.uuid,
            amount,
            qmoney_payer,
        )

        actual = gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'][
            'ok'], f'should have returned ok, but got {actual}'
        assert actual['data']['requestQmoneyPayment']['qmoneyPayment'][
            'uuid'] is not None
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['uuid'],
                'policy_uuid':
                f'{one_policy.uuid}',
                'status':
                'WAITING_FOR_CONFIRMATION',
                'amount':
                amount,
                'payer_wallet':
                qmoney_payer,
                'transaction_id':
                actual['data']['requestQmoneyPayment']['qmoneyPayment']
                ['externalTransactionId']
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

    def test_failing_at_requesting_qmoney_payment_for_an_existing_given_non_idle_policy(
            self, gql_client, one_policy, qmoney_payer):
        one_policy.status = Policy.STATUS_ACTIVE
        one_policy.save()
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
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            one_policy.uuid,
            amount,
            qmoney_payer,
        )

        actual = gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == f'Something went wrong. The payment could not be requested. The transaction is INITIATED. Reason: The Policy {one_policy.uuid} should be Idle but it is not.'

    def test_failing_at_requesting_qmoney_payment_for_an_absent_given_policy(
            self, gql_client, qmoney_payer):
        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            uuid.uuid4(),
            0,
            qmoney_payer,
        )

        actual = gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'] is None
        assert actual['errors'][0][
            'message'] == 'The UUID does not correspond to any existing policy.'

    def test_failing_at_requesting_qmoney_payment_without_policy(
            self, gql_client):
        query = '''
        mutation {
          requestQmoneyPayment() {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        '''

        actual = gql_client.execute(query)
        assert 'Syntax Error GraphQL (3:32) Expected Name' in actual['errors'][
            0]['message']

    @pytest.mark.with_gmail
    def test_requesting_and_proceeding_qmoney_payment_for_an_existing_given_policy(
            self, gql_client, one_policy, qmoney_payer, gmail_client):
        amount = 1
        before_initiating_transaction = current_datetime()

        query = '''
        mutation {
          requestQmoneyPayment(policyUuid: "%s", amount: %i, payerWallet: "%s") {
            qmoneyPayment {
              uuid
              status
              amount
              payerWallet
              policyUuid
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            one_policy.uuid,
            amount,
            qmoney_payer,
        )

        actual = gql_client.execute(query)
        assert actual['data']['requestQmoneyPayment'][
            'ok'], 'should have returned ok'
        uuid = actual['data']['requestQmoneyPayment']['qmoneyPayment']['uuid']
        assert uuid is not None
        transaction_id = actual['data']['requestQmoneyPayment'][
            'qmoneyPayment']['externalTransactionId']
        expected = self.generate_expected_mutation_ok_response(
            'requestQmoneyPayment', {
                'uuid': uuid,
                'policy_uuid': f'{one_policy.uuid}',
                'status': 'WAITING_FOR_CONFIRMATION',
                'amount': amount,
                'payer_wallet': qmoney_payer,
                'transaction_id': transaction_id,
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            gmail_client, 10, 300)

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
              contributionUuid
              externalTransactionId
            }
            ok
          }
        }
        ''' % (
            uuid,
            otp,
        )

        actual = gql_client.execute(query)
        expected = self.generate_expected_mutation_ok_response(
            'proceedQmoneyPayment', {
                'uuid': uuid,
                'policy_uuid': f'{one_policy.uuid}',
                'status': 'PROCEEDED',
                'amount': amount,
                'payer_wallet': qmoney_payer,
                'transaction_id': transaction_id,
            })
        assert actual == expected, f'should have been {expected}, but we got {actual}'