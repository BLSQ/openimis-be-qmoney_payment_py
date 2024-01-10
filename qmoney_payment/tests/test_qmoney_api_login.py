import json
import os
import pytest
import requests

from helpers import QMoneyBasicAuth, QMoney


class TestQmoneyAPILogin:

    def test_logging_in_to_qmoney(self, qmoney_url, qmoney_credentials,
                                  qmoney_token):
        response = QMoney.login(qmoney_url, qmoney_credentials, qmoney_token,
                                True)
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == '1'
        assert json_response['responseMessage'] == 'Success'

        data = json_response['data']
        assert data['twoFactorEnable'] == 'false'
        assert data['accessTokenExpiry'] == '-1'
        assert data['access_token'] is not None

    def test_failing_at_logging_in_to_qmoney_when_wrong_authorization_token(
            self, qmoney_url, qmoney_credentials):
        response = QMoney.login(qmoney_url, qmoney_credentials, 'token', True)

        assert response.status_code == 401

        json_response = response.json()
        assert json_response['error'] == 'unauthorized'
        assert json_response[
            'error_description'] == 'Full authentication is required to access this resource'

    def test_failing_at_logging_in_to_qmoney_when_missing_initial_authorization_token(
            self, qmoney_url, qmoney_credentials):
        json_payload = {
            "grantType": "password",
            "username": qmoney_credentials[0],
            "password": qmoney_credentials[1],
        }
        response = requests.post(url=f'{qmoney_url}/login', json=json_payload)
        assert response.status_code == 401

        json_response = response.json()
        assert json_response['error'] == 'Unauthorized'
        assert json_response['message'] == 'Unauthorized'
        assert json_response['status'] == 401

    def test_failing_at_logging_in_to_qmoney_when_wrong_grantType(
            self, qmoney_url, qmoney_credentials, qmoney_token):
        json_payload = {
            "grantType": "client_credentials",
            "username": qmoney_credentials[0],
            "password": qmoney_credentials[1],
        }

        response = requests.post(url=f'{qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(qmoney_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == '-5100006'
        assert json_response['responseMessage'] == 'Invalid Nonce Block Node'

    def test_failing_at_logging_in_to_qmoney_when_missing_parameter_grant_type(
            self, qmoney_url, qmoney_credentials, qmoney_token):
        json_payload = {
            "username": qmoney_credentials[0],
            "password": qmoney_credentials[1],
        }

        response = requests.post(url=f'{qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(qmoney_token))
        assert response.status_code == 200
        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : GrantType'

    def test_failing_at_logging_in_to_qmoney_when_wrong_username(
            self, qmoney_url, qmoney_credentials, qmoney_token):

        response = QMoney.login(qmoney_url,
                                ['username', qmoney_credentials[1]],
                                qmoney_token, True)

        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150024
        assert json_response[
            'responseMessage'] == 'UserAccount not found from cache. UserIdentifier : username'

    def test_failing_at_logging_in_to_qmoney_when_missing_username(
            self, qmoney_url, qmoney_credentials, qmoney_token):
        json_payload = {
            "grantType": "password",
            "password": qmoney_credentials[1],
        }

        response = requests.post(url=f'{qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(qmoney_token))
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : UserName'

    def test_failing_at_logging_in_to_qmoney_when_missing_password(
            self, qmoney_url, qmoney_credentials, qmoney_token):
        json_payload = {
            "grantType": "password",
            "username": qmoney_credentials[0],
        }

        response = requests.post(url=f'{qmoney_url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(qmoney_token))
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == -150008
        assert json_response[
            'responseMessage'] == 'Mandatory parameter is missing : Password'

    def test_failing_at_logging_in_to_qmoney_when_wrong_password(
            self, qmoney_url, qmoney_credentials, qmoney_token):

        response = QMoney.login(qmoney_url,
                                [qmoney_credentials[0], 'password'],
                                qmoney_token, True)
        # json_payload = {
        #     "grantType": "password",
        #     "username": qmoney_credentials[0],
        #     "password": "password",
        # }

        # response = requests.post(url=f'{qmoney_url}/login',
        #                          json=json_payload,
        #                          auth=QMoneyBasicAuth(qmoney_token))
        assert response.status_code == 200

        json_response = response.json()
        assert json_response['responseCode'] == '-5100002'
        assert json_response[
            'responseMessage'] == 'Invalid username or password'
