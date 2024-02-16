import json
import os
import requests
from unittest import TestCase

from .helpers import QMoneyBasicAuth, QMoney
from .qmoney_helpers import qmoney_url, qmoney_token, qmoney_credentials


class TestQmoneyAPILogin(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._qmoney_url = qmoney_url()
        cls._qmoney_credentials = qmoney_credentials()
        cls._qmoney_token = qmoney_token()

    def test_logging_in_to_qmoney(self):
        response = QMoney.login(TestQmoneyAPILogin._qmoney_url,
                                TestQmoneyAPILogin._qmoney_credentials,
                                TestQmoneyAPILogin._qmoney_token, True)
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'Success'

        data = json_response['data']
        assert data['twoFactorEnable'] == 'false'
        assert data['accessTokenExpiry'] == '-1'
        assert data['access_token'] is not None

    def test_failing_at_logging_in_to_qmoney_when_wrong_authorization_token(
            self):
        response = QMoney.login(TestQmoneyAPILogin._qmoney_url,
                                TestQmoneyAPILogin._qmoney_credentials,
                                'token', True)

        assert response.status_code == 401

        json_response = response.json()
        assert json_response['error'] == 'unauthorized'
        assert json_response[
            'error_description'] == 'Full authentication is required to access this resource'

    def test_failing_at_logging_in_to_qmoney_when_missing_initial_authorization_token(
            self):
        json_payload = {
            "grantType": "password",
            "username": TestQmoneyAPILogin._qmoney_credentials[0],
            "password": TestQmoneyAPILogin._qmoney_credentials[1],
        }
        response = requests.post(url=f'{TestQmoneyAPILogin._qmoney_url}/login',
                                 json=json_payload)
        assert response.status_code == 401

        json_response = response.json()
        assert json_response['error'] == 'Unauthorized'
        assert json_response['message'] == 'Unauthorized'
        assert json_response['status'] == 401

    def test_failing_at_logging_in_to_qmoney_when_wrong_grantType(self):
        json_payload = {
            "grantType": "client_credentials",
            "username": TestQmoneyAPILogin._qmoney_credentials[0],
            "password": TestQmoneyAPILogin._qmoney_credentials[1],
        }

        response = requests.post(url=f'{TestQmoneyAPILogin._qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(
                                     TestQmoneyAPILogin._qmoney_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '-5100006'
        assert json_response['responseMessage'] == 'Invalid Nonce Block Node'

    def test_failing_at_logging_in_to_qmoney_when_missing_parameter_grant_type(
            self):
        json_payload = {
            "username": TestQmoneyAPILogin._qmoney_credentials[0],
            "password": TestQmoneyAPILogin._qmoney_credentials[1],
        }

        response = requests.post(url=f'{TestQmoneyAPILogin._qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(
                                     TestQmoneyAPILogin._qmoney_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : GrantType'

    def test_failing_at_logging_in_to_qmoney_when_wrong_username(self):

        response = QMoney.login(
            TestQmoneyAPILogin._qmoney_url,
            ['username', TestQmoneyAPILogin._qmoney_credentials[1]],
            TestQmoneyAPILogin._qmoney_token, True)

        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150024
        assert json_response[
            'responseMessage'] == 'UserAccount not found from cache. UserIdentifier : username'

    def test_failing_at_logging_in_to_qmoney_when_missing_username(self):
        json_payload = {
            "grantType": "password",
            "password": TestQmoneyAPILogin._qmoney_credentials[1],
        }

        response = requests.post(url=f'{TestQmoneyAPILogin._qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(
                                     TestQmoneyAPILogin._qmoney_token))
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : UserName'

    def test_failing_at_logging_in_to_qmoney_when_missing_password(self):
        json_payload = {
            "grantType": "password",
            "username": TestQmoneyAPILogin._qmoney_credentials[0],
        }

        response = requests.post(url=f'{TestQmoneyAPILogin._qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(
                                     TestQmoneyAPILogin._qmoney_token))
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : Password'

    def test_failing_at_logging_in_to_qmoney_when_wrong_password(self):

        response = QMoney.login(
            TestQmoneyAPILogin._qmoney_url,
            [TestQmoneyAPILogin._qmoney_credentials[0], 'password'],
            TestQmoneyAPILogin._qmoney_token, True)

        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == '-5100002'
        assert json_response[
            'responseMessage'] == 'Invalid username or password'
