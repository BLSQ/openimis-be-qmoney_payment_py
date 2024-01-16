import pytest
import requests
import json
import pprint

from helpers import QMoneyBearerAuth, QMoney, set_into, del_from, gmail_wait_and_get_recent_emails_with_qmoney_otp, extract_otp_from_email_messages, gmail_mark_messages_as_read, current_datetime


@pytest.mark.with_gmail
class TestQmoneyAPIVerifyCode:

    @pytest.fixture(scope="function")
    def transaction_id_and_otp(self, request, qmoney_access_token, qmoney_url,
                               qmoney_payer, qmoney_payee,
                               qmoney_payee_pin_code, gmail_client):
        # can be proceeded one and only once
        before_initiating_transaction = current_datetime()

        marker = request.node.get_closest_marker("amount_to_pay")
        amount = 1
        if marker is not None:
            amount = marker.args[0]
        response = QMoney.initiate_transaction(qmoney_url, qmoney_access_token,
                                               qmoney_payer, qmoney_payee,
                                               amount, qmoney_payee_pin_code)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'OTP Send Successfully'
        assert json_response['data']['transactionId'] is not None

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        transaction_id = json_response['data']['transactionId']

        return (transaction_id, otp)

    def test_proceeding_normal_transaction(self, qmoney_access_token,
                                           qmoney_url, transaction_id_and_otp):
        transaction_id, otp = transaction_id_and_otp

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, otp)
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

    @pytest.mark.amount_to_pay(1000000000)
    def test_proceeding_transaction_with_too_big_amount(
            self, qmoney_access_token, qmoney_url, transaction_id_and_otp,
            qmoney_payer):
        transaction_id, otp = transaction_id_and_otp

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response[
            'responseCode'] == '-120008', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Balance not sufficient for PouchExId : EMONEY_POUCH , userIdentifier : {qmoney_payer}', f'response body is {response.text}'
        assert json_response['data']['balanceData'] == [{}]
        # it is the wallet of the payee!!

    def test_proceeding_transaction_twice(self, qmoney_access_token,
                                          qmoney_url, transaction_id_and_otp):
        transaction_id, otp = transaction_id_and_otp

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response[
            'responseCode'] == '1', f'response body is {response.text}'
        assert json_response['responseMessage'] == 'Success'

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, otp)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -150001, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Adapter Session Not Found session id : {transaction_id} event : CLIENT_ADAPTER_VERIFYOTP_REQUEST '

    def test_failing_at_confirming_transaction_when_empty_payload(
            self, qmoney_access_token, qmoney_url):
        json_payload = {}

        response = requests.post(url=f'{qmoney_url}/verifyCode',
                                 json=json_payload,
                                 auth=QMoneyBearerAuth(qmoney_access_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -20002, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Mandatory parmater missing : transactionId'

    def test_failing_at_proceeding_transaction_when_wrong_or_missing_transaction_id(
            self, qmoney_access_token, qmoney_url, transaction_id_and_otp):

        _, otp = transaction_id_and_otp
        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              None, otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -20002, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Mandatory parmater missing : transactionId'

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              'txn_fake', otp)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == -150001, f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == 'Adapter Session Not Found session id : txn_fake event : CLIENT_ADAPTER_VERIFYOTP_REQUEST '

    def test_failing_at_proceeding_transaction_when_wrong_or_missing_otp(
            self, qmoney_access_token, qmoney_url, transaction_id_and_otp):

        transaction_id, _ = transaction_id_and_otp
        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, None)

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == '-150005', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, 'otp')

        assert response.status_code == 200
        json_response = response.json()
        assert json_response[
            'responseCode'] == '-150005', f'response body is {response.text}'
        assert json_response[
            'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

    def test_proceeding_transaction_after_20_failed_attemps_with_wrong_otp(
            self, qmoney_access_token, qmoney_url, transaction_id_and_otp):

        transaction_id, correct_otp = transaction_id_and_otp

        for i in range(20):
            response = QMoney.proceed_transaction(qmoney_url,
                                                  qmoney_access_token,
                                                  transaction_id, '000000')

            assert response.status_code == 200
            json_response = response.json()
            assert json_response[
                'responseCode'] == '-150005', f'response body is {response.text}'
            assert json_response[
                'responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

        response = QMoney.proceed_transaction(qmoney_url, qmoney_access_token,
                                              transaction_id, correct_otp)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['data']['transactionId'] == transaction_id
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'Success'
        wallet = next((wallet
                       for wallet in json_response['data']['balanceData']
                       if wallet['walletExternalId'] == 'MAIN_WALLET'
                       and wallet['pouchExternalId'] == 'EMONEY_POUCH'), None)
        assert wallet is not None