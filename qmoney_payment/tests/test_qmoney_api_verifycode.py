import os
import pytest
import json
import pprint
import requests
import time
import unittest
from unittest import TestCase

from simplegmail import Gmail

from .helpers import QMoneyBearerAuth, QMoney, set_into, del_from, gmail_wait_and_get_recent_emails_with_qmoney_otp, extract_otp_from_email_messages, gmail_mark_messages_as_read, current_datetime, gmail_mark_as_read_recent_emails_with_qmoney_otp
from .qmoney_helpers import qmoney_url, qmoney_credentials, qmoney_access_token, qmoney_getmoney_json_payload, qmoney_payee, qmoney_payer, qmoney_payee_pin_code


@unittest.skipIf('RUN_ALSO_TESTS_WITH_GMAIL' not in os.environ,
                 'Skipping tests using Gmail')
class TestQmoneyAPIVerifyCode(TestCase):

    @classmethod
    def gmail_client(cls):
        client = Gmail()
        time.sleep(5)
        gmail_mark_as_read_recent_emails_with_qmoney_otp(client)
        return client

    @classmethod
    def setUpClass(cls):
        cls._qmoney_url = qmoney_url()
        cls._qmoney_credentials = qmoney_credentials()
        cls._qmoney_access_token = qmoney_access_token()
        cls._qmoney_payee = qmoney_payee()
        cls._qmoney_payer = qmoney_payer()
        cls._qmoney_payee_pin_code = qmoney_payee_pin_code()
        cls._gmail_client = cls.gmail_client()

    @classmethod
    def tearDownClass(cls):
        gmail_mark_as_read_recent_emails_with_qmoney_otp(cls._gmail_client)

    def transaction_id_and_otp(self, amount=1):
        # can be proceeded one and only once
        before_initiating_transaction = current_datetime()

        response = QMoney.initiate_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token,
            TestQmoneyAPIVerifyCode._qmoney_payer,
            TestQmoneyAPIVerifyCode._qmoney_payee, amount,
            TestQmoneyAPIVerifyCode._qmoney_payee_pin_code)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'OTP Send Successfully'
        assert json_response['data']['transactionId'] is not None

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            TestQmoneyAPIVerifyCode._gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        transaction_id = json_response['data']['transactionId']

        return (transaction_id, otp)

    def test_proceeding_normal_transaction(self):
        transaction_id, otp = self.transaction_id_and_otp()

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response[
            'responseCode'] == '1', f'response body is {response.text}'
        assert json_response['responseMessage'] == 'Success'
        wallet = next((wallet
                       for wallet in json_response['data']['balanceData']
                       if wallet['walletExternalId'] == 'MAIN_WALLET'
                       and wallet['pouchExternalId'] == 'EMONEY_POUCH'), None)
        assert wallet is not None
        # it is the wallet of the payee/merchant!!
        # here an example of the returned payload:
        # {
        #     "data":
        #     {
        #         "transactionId": "txn_17067100139046477831",
        #         "balanceData":
        #         [
        #             {
        #                 "walletExternalId": "MAIN_WALLET",
        #                 "usedValue": 0,
        #                 "unusedValue": 28600000,
        #                 "availableBalance": "286.00",
        #                 "pouchExternalId": "EMONEY_POUCH",
        #                 "ValidFromDate": "2023-06-21 09:48:24.000",
        #                 "ValidToDate": "2036-01-01 04:59:59.000"
        #             },
        #             {
        #                 "ValidToDate": "2036-01-01 04:59:59.000",
        #                 "usedValue": 0,
        #                 "pouchExternalId": "LOYALTY_POINTS_POUCH",
        #                 "ValidFromDate": "2023-06-21 09:48:24.000",
        #                 "walletExternalId": "MAIN_WALLET",
        #                 "unusedValue": 0,
        #                 "availableBalance": "0"
        #             }
        #         ]
        #     },
        #     "responseCode": "1",
        #     "responseMessage": "Success"
        # }

    def test_proceeding_transaction_with_too_big_amount(self):
        transaction_id, otp = self.transaction_id_and_otp(1000000000)

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response[
            'responseCode'] == '-120008', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Balance not sufficient for PouchExId : EMONEY_POUCH , userIdentifier : {TestQmoneyAPIVerifyCode._qmoney_payer}', f'response body is {response.text}'
        assert json_response['data']['balanceData'] == [{}]
        # it is the wallet of the payee!!

    def test_proceeding_transaction_twice(self, ):
        transaction_id, otp = self.transaction_id_and_otp()

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response[
            'responseCode'] == '1', f'response body is {response.text}'
        assert json_response['responseMessage'] == 'Success'

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id, otp)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -150001, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Adapter Session Not Found session id : {transaction_id} event : CLIENT_ADAPTER_VERIFYOTP_REQUEST '

    def test_failing_at_confirming_transaction_when_empty_payload(self):
        json_payload = {}

        response = requests.post(
            url=f'{TestQmoneyAPIVerifyCode._qmoney_url}/verifyCode',
            json=json_payload,
            auth=QMoneyBearerAuth(
                TestQmoneyAPIVerifyCode._qmoney_access_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -20002, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Mandatory parmater missing : transactionId'

    def test_failing_at_proceeding_transaction_when_wrong_or_missing_transaction_id(
            self):

        _, otp = self.transaction_id_and_otp()
        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, None, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -20002, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Mandatory parmater missing : transactionId'

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, 'txn_fake', otp)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -150001, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Adapter Session Not Found session id : txn_fake event : CLIENT_ADAPTER_VERIFYOTP_REQUEST '

    def test_failing_at_proceeding_transaction_when_wrong_or_missing_otp(self):

        transaction_id, _ = self.transaction_id_and_otp()
        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id, None)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == '-150005', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id,
            'otp')

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == '-150005', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

    def test_proceeding_transaction_after_20_failed_attemps_with_wrong_otp(
            self):

        transaction_id, correct_otp = self.transaction_id_and_otp()

        for i in range(20):
            response = QMoney.proceed_transaction(
                TestQmoneyAPIVerifyCode._qmoney_url,
                TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id,
                '000000')

            assert response.status_code == 200
            json_response = response.json()
            assert json_response[
                'responseCode'] == '-150005', f'response body is {response.text}'
            assert json_response[
                'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

        response = QMoney.proceed_transaction(
            TestQmoneyAPIVerifyCode._qmoney_url,
            TestQmoneyAPIVerifyCode._qmoney_access_token, transaction_id,
            correct_otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response['responseCode'] == '1', , f'response body is {response.text}'
        assert json_response['responseMessage'] == 'Success'
        wallet = next((wallet
                       for wallet in json_response['data']['balanceData']
                       if wallet['walletExternalId'] == 'MAIN_WALLET'
                       and wallet['pouchExternalId'] == 'EMONEY_POUCH'), None)
        assert wallet is not None