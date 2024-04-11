import json
import os
import requests
import time
from unittest import TestCase

from simplegmail import Gmail

from .helpers import QMoneyBearerAuth, QMoney, set_into, del_from, gmail_mark_as_read_recent_emails_with_qmoney_otp
from .qmoney_helpers import qmoney_url, qmoney_token, qmoney_credentials, qmoney_access_token, qmoney_getmoney_json_payload, qmoney_payee, qmoney_payer, qmoney_payee_pin_code


class TestQmoneyAPIGetMoney(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._qmoney_url = qmoney_url()
        cls._qmoney_credentials = qmoney_credentials()
        cls._qmoney_token = qmoney_token()
        cls._qmoney_access_token = qmoney_access_token()
        cls._qmoney_payee = qmoney_payee()
        cls._qmoney_payer = qmoney_payer()
        cls._qmoney_payee_pin_code = qmoney_payee_pin_code()

    @classmethod
    def tearDownClass(cls):
        if 'RUN_ALSO_TESTS_WITH_GMAIL' in os.environ:
            client = Gmail()
            time.sleep(30)
            gmail_mark_as_read_recent_emails_with_qmoney_otp(client)

    def test_initiating_transaction(self):
        amount = 1
        response = QMoney.initiate_transaction(
            TestQmoneyAPIGetMoney._qmoney_url,
            TestQmoneyAPIGetMoney._qmoney_access_token,
            TestQmoneyAPIGetMoney._qmoney_payer,
            TestQmoneyAPIGetMoney._qmoney_payee, amount,
            TestQmoneyAPIGetMoney._qmoney_payee_pin_code)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'OTP Send Successfully'
        assert json_response['data']['transactionId'] is not None

    def test_failing_at_initiating_transaction_when_missing_access_token(self):
        json_payload = qmoney_getmoney_json_payload()

        response = requests.post(
            url=f'{TestQmoneyAPIGetMoney._qmoney_url}/getMoney',
            json=json_payload)
        assert response.status_code == 401
        json_response = response.json()
        assert json_response['error'] == 'unauthorized'
        assert json_response[
            'error_description'] == 'Full authentication is required to access this resource'

    def test_failing_at_initiating_transaction_when_wrong_access_token(self):

        amount = 1
        fake_access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dnaW5nQXMiOm51bGwsImF1ZCI6WyJBZGFwdGVyX09hdXRoX1Jlc291cmNlX1NlcnZlciJdLCJncmFudF90eXBlIjoicGFzc3dvcmQiLCJkZXZpY2VVbmlxdWVJZCI6bnVsbCwidXNlcl9uYW1lIjoiMTQwMDE1MDIiLCJzY'
        response = QMoney.initiate_transaction(
            TestQmoneyAPIGetMoney._qmoney_url, fake_access_token,
            TestQmoneyAPIGetMoney._qmoney_payer,
            TestQmoneyAPIGetMoney._qmoney_payee, amount,
            TestQmoneyAPIGetMoney._qmoney_payee_pin_code)
        assert response.status_code == 401
        json_response = response.json()
        assert json_response['error'] == 'invalid_token'
        assert json_response[
            'error_description'] == 'Cannot convert access token to JSON'

    def test_failing_but_succeeding_at_initiating_transaction_when_missing_input_parameter(
            self):
        several_key_paths_in_payload = [['data', 'fromUser', 'userIdentifier'],
                                        ['data', 'toUser', 'userIdentifier'],
                                        ['data', 'serviceId'],
                                        ['data', 'productId'],
                                        ['data', 'remarks'],
                                        ['data', 'payment'],
                                        ['data', 'transactionPin']]
        for key_path in several_key_paths_in_payload:
            with self.subTest(msg=f'for parameter {".".join(key_path)}',
                              key_path=key_path):
                json_payload = qmoney_getmoney_json_payload()

                del_from(json_payload, key_path)

                response = requests.post(
                    url=f'{TestQmoneyAPIGetMoney._qmoney_url}/getMoney',
                    json=json_payload,
                    auth=QMoneyBearerAuth(
                        TestQmoneyAPIGetMoney._qmoney_access_token))
                # Expecting a failure but Qmoney actually accepts and sends an OTP
                assert response.status_code == 200
                json_response = response.json()
                assert json_response['responseCode'] == '1'
                assert json_response[
                    'responseMessage'] == 'OTP Send Successfully'

    def test_failing_but_succeeding_at_initiating_transaction_when_wrong_input_parameter(
            self):
        several_key_paths_in_payload = [['data', 'fromUser', 'userIdentifier'],
                                        ['data', 'toUser', 'userIdentifier'],
                                        ['data', 'serviceId'],
                                        ['data', 'productId'],
                                        ['data', 'remarks'],
                                        ['data', 'payment'],
                                        ['data', 'transactionPin']]
        for key_path in several_key_paths_in_payload:
            with self.subTest(msg=f'for parameter {".".join(key_path)}',
                              key_path=key_path):
                json_payload = qmoney_getmoney_json_payload()

                if key_path[1] == 'payment':
                    set_into(json_payload, key_path, [{}])
                else:
                    set_into(json_payload, key_path, key_path[-1])

                response = requests.post(
                    url=f'{TestQmoneyAPIGetMoney._qmoney_url}/getMoney',
                    json=json_payload,
                    auth=QMoneyBearerAuth(
                        TestQmoneyAPIGetMoney._qmoney_access_token))
                # Expecting a failure but Qmoney actually accepts and sends an OTP
                assert response.status_code == 200
                json_response = response.json()
                assert json_response[
                    'responseCode'] == '1', f'We expected 1 but got {json_response["responseCode"]}. The full payload is {response.text}'
                assert json_response[
                    'responseMessage'] == 'OTP Send Successfully'

    def test_failing_but_succeeding_at_initiating_transaction_when_the_payload_is_empty(
            self):
        json_payload = qmoney_getmoney_json_payload()
        del json_payload['data']

        response = requests.post(
            url=f'{TestQmoneyAPIGetMoney._qmoney_url}/getMoney',
            json=json_payload,
            auth=QMoneyBearerAuth(TestQmoneyAPIGetMoney._qmoney_access_token))
        # Expecting a failure but Qmoney actually accepts and sends an OTP
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'OTP Send Successfully'
