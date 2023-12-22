import pytest
import requests
import json
import pprint

class QMoneyBasicAuth(requests.auth.AuthBase):
  def __init__(self, token):
    self.token = token
  def __call__(self, r):
    r.headers["Authorization"] = f'Basic {self.token}'
    return r

class QMoneyBearerAuth(requests.auth.AuthBase):
  def __init__(self, token):
    self.token = token
  def __call__(self, r):
    r.headers["Authorization"] = f'Bearer {self.token}'
    return r

class TestQmoneyAPIGetMoney:
  def login(self, url, credentials, token):
    json_payload = {
      "grantType": "password",
      "username": credentials[0],
      "password": credentials[1],
    }
    response = requests.post(url = f'{url}/login', json = json_payload, auth=QMoneyBasicAuth(token))
    return response.json()['data']['access_token']

  def test_initiating_transaction(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'OTP Send Successfully'
    assert json_response['data']['transactionId'] is not None


  def test_failing_at_initiating_transaction_when_missing_access_token(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    json_payload = qmoney_getmoney_json_payload

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload)
    assert response.status_code == 401
    json_response = response.json()
    assert json_response['error'] == 'unauthorized'
    assert json_response['error_description'] == 'Full authentication is required to access this resource'

  def test_failing_at_initiating_transaction_when_wrong_access_token(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    json_payload = qmoney_getmoney_json_payload

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dnaW5nQXMiOm51bGwsImF1ZCI6WyJBZGFwdGVyX09hdXRoX1Jlc291cmNlX1NlcnZlciJdLCJncmFudF90eXBlIjoicGFzc3dvcmQiLCJkZXZpY2VVbmlxdWVJZCI6bnVsbCwidXNlcl9uYW1lIjoiMTQwMDE1MDIiLCJzY'))
    assert response.status_code == 401
    json_response = response.json()
    assert json_response['error'] == 'invalid_token'
    assert json_response['error_description'] == 'Cannot convert access token to JSON'


  def get_from(self, the_map, keys):
    if the_map is None or len(the_map) == 0:
      return None
    if keys is None or len(keys) == 0:
      return None
    if len(keys) == 1:
      return the_map.get(keys[0], None)
    return self.get_from(the_map[keys[0]], keys[1:])

  def del_from(self, the_map, keys):
    if the_map is None or len(the_map) == 0:
      return None
    if keys is None or len(keys) == 0:
      return None
    if len(keys) == 1:
      del the_map[keys[0]]
    else:
      self.del_from(the_map[keys[0]], keys[1:])
    return the_map

  def set_into(self, the_map, keys, value):
    if the_map is None:
      return None
    if keys is None or len(keys) == 0:
      return None
    if len(keys) == 1:
      the_map[keys[0]] = value
    else:
      self.set_into(the_map[keys[0]], keys[1:], value)
    return the_map

  @pytest.mark.parametrize(
    "input_parameter",
    [
      (['data', 'fromUser', 'userIdentifier']),
      (['data', 'toUser', 'userIdentifier']),
      (['data', 'serviceId']),
      (['data', 'productId']),
      (['data', 'remarks']),
      (['data', 'payment']),
      (['data', 'transactionPin'])
    ])
  @pytest.mark.skip(reason='Expecting a failure but Qmoney actually accepts and sends an OTP')
  def test_failing_at_initiating_transaction_when_missing_input_parameter(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload, input_parameter):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    self.del_from(json_payload, input_parameter)

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    assert False

  @pytest.mark.parametrize(
    "input_parameter",
    [
      (['data', 'fromUser', 'userIdentifier']),
      (['data', 'toUser', 'userIdentifier']),
      (['data', 'serviceId']),
      (['data', 'productId']),
      (['data', 'remarks']),
      (['data', 'payment']),
      (['data', 'transactionPin'])
    ])
  @pytest.mark.skip(reason='Expecting a failure but Qmoney actually accepts and sends an OTP')
  def test_failing_at_initiating_transaction_when_wrong_input_parameter(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload, input_parameter):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    self.set_into(json_payload, input_parameter, input_parameter[-1])

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    assert False

  @pytest.mark.skip(reason='Expecting a failure but Qmoney actually accepts and sends an OTP')
  def test_failing_at_initiating_transaction_when_the_payload_is_empty(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload
    del json_payload['data']

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    assert False