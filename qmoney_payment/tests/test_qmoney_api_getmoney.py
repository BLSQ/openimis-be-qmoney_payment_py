import json
import pprint
import pytest
import requests

from helpers import QMoneyBearerAuth, QMoney, set_into, del_from


class TestQmoneyAPIGetMoney:

  def test_initiating_transaction(self, qmoney_access_token, qmoney_url,
                                  qmoney_payer, qmoney_payee,
                                  qmoney_payee_pin_code):
    amount = 1
    response = QMoney.initiate_transaction(qmoney_url, qmoney_access_token,
                                           qmoney_payer, qmoney_payee, amount,
                                           qmoney_payee_pin_code)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'OTP Send Successfully'
    assert json_response['data']['transactionId'] is not None

  def test_failing_at_initiating_transaction_when_missing_access_token(
      self, qmoney_url, qmoney_credentials, qmoney_token,
      qmoney_getmoney_json_payload):
    json_payload = qmoney_getmoney_json_payload

    response = requests.post(url=f'{qmoney_url}/getMoney', json=json_payload)
    assert response.status_code == 401
    json_response = response.json()
    assert json_response['error'] == 'unauthorized'
    assert json_response[
        'error_description'] == 'Full authentication is required to access this resource'

  def test_failing_at_initiating_transaction_when_wrong_access_token(
      self, qmoney_url, qmoney_payer, qmoney_payee, qmoney_payee_pin_code):

    amount = 1
    fake_access_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dnaW5nQXMiOm51bGwsImF1ZCI6WyJBZGFwdGVyX09hdXRoX1Jlc291cmNlX1NlcnZlciJdLCJncmFudF90eXBlIjoicGFzc3dvcmQiLCJkZXZpY2VVbmlxdWVJZCI6bnVsbCwidXNlcl9uYW1lIjoiMTQwMDE1MDIiLCJzY'
    response = QMoney.initiate_transaction(qmoney_url, fake_access_token,
                                           qmoney_payer, qmoney_payee, amount,
                                           qmoney_payee_pin_code)
    assert response.status_code == 401
    json_response = response.json()
    assert json_response['error'] == 'invalid_token'
    assert json_response[
        'error_description'] == 'Cannot convert access token to JSON'

  @pytest.mark.parametrize("input_parameter",
                           [(['data', 'fromUser', 'userIdentifier']),
                            (['data', 'toUser', 'userIdentifier']),
                            (['data', 'serviceId']), (['data', 'productId']),
                            (['data', 'remarks']), (['data', 'payment']),
                            (['data', 'transactionPin'])])
  @pytest.mark.skip(
      reason='Expecting a failure but Qmoney actually accepts and sends an OTP'
  )
  def test_failing_at_initiating_transaction_when_missing_input_parameter(
      self, qmoney_access_token, qmoney_url, qmoney_getmoney_json_payload,
      input_parameter):
    json_payload = qmoney_getmoney_json_payload

    del_from(json_payload, input_parameter)

    response = requests.post(url=f'{qmoney_url}/getMoney',
                             json=json_payload,
                             auth=QMoneyBearerAuth(qmoney_access_token))
    assert response.status_code == 200
    assert False

  @pytest.mark.parametrize("input_parameter",
                           [(['data', 'fromUser', 'userIdentifier']),
                            (['data', 'toUser', 'userIdentifier']),
                            (['data', 'serviceId']), (['data', 'productId']),
                            (['data', 'remarks']), (['data', 'payment']),
                            (['data', 'transactionPin'])])
  @pytest.mark.skip(
      reason='Expecting a failure but Qmoney actually accepts and sends an OTP'
  )
  def test_failing_at_initiating_transaction_when_wrong_input_parameter(
      self, qmoney_access_token, qmoney_url, qmoney_getmoney_json_payload,
      input_parameter):
    json_payload = qmoney_getmoney_json_payload

    set_into(json_payload, input_parameter, input_parameter[-1])

    response = requests.post(url=f'{qmoney_url}/getMoney',
                             json=json_payload,
                             auth=QMoneyBearerAuth(qmoney_access_token))
    assert response.status_code == 200
    assert False

  @pytest.mark.skip(
      reason='Expecting a failure but Qmoney actually accepts and sends an OTP'
  )
  def test_failing_at_initiating_transaction_when_the_payload_is_empty(
      self, qmoney_access_token, qmoney_url, qmoney_getmoney_json_payload):
    json_payload = qmoney_getmoney_json_payload
    del json_payload['data']

    response = requests.post(url=f'{qmoney_url}/getMoney',
                             json=json_payload,
                             auth=QMoneyBearerAuth(qmoney_access_token))
    assert response.status_code == 200
    assert False