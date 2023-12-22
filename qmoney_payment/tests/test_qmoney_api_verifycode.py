import pytest
import requests
import json
import pprint
from simplegmail import Gmail
from simplegmail.query import construct_query
import time
import re
from datetime import datetime, timezone, timedelta

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

class TestQmoneyAPIVerifyCode:
  def login(self, url, credentials, token):
    json_payload = {
      "grantType": "password",
      "username": credentials[0],
      "password": credentials[1],
    }
    response = requests.post(url = f'{url}/login', json = json_payload, auth=QMoneyBasicAuth(token))
    return response.json()['data']['access_token']

  def test_confirming_transaction(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    before_initiating_transaction = datetime.now(tz = timezone(timedelta(hours = 1)))

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'OTP Send Successfully'
    assert json_response['data']['transactionId'] is not None

    gmail = Gmail()

    mustend = time.time() + 300

    messages = []
    while time.time() < mustend and len(messages) == 0:
      messages = gmail.get_messages(query=construct_query(unread=True, sender='alerts@qmoney.gm', subject='Otp - QCell', newer_than=(1, 'day')))
      messages.sort(key=lambda msg: msg.date)
      time.sleep(5)

    assert len(messages) > 0, 'No new email message with the sent OTP found'
    [message.mark_as_read() for message in messages]

    message = messages[-1]
    assert datetime.fromisoformat(message.date) > before_initiating_transaction, 'the date of the message is earlier than the time the request has been made'
    match = re.search(r"Generated OTP : \d+", message.html)

    assert match is not None, 'No OTP found in the most recent retrieved email'

    otp = match.group(0).replace('Generated OTP : ', '')
    transaction_id = json_response['data']['transactionId']

    json_payload = {
      'transactionId': transaction_id,
      'otp': otp 
    }

    response = requests.post(url = f'{qmoney_url}/verifyCode', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['data']['transactionId'] == transaction_id
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'Success'
    wallet = next((wallet for wallet in json_response['data']['balanceData'] if wallet['walletExternalId'] == 'MAIN_WALLET' and wallet['pouchExternalId'] == 'EMONEY_POUCH'), None)
    assert wallet is not None
    assert wallet['usedValue'] == qmoney_getmoney_json_payload['data']['payment'][0]['amount']
    assert response.text == ''

  def test_failing_at_confirming_transaction_when_empty_payload(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)

    json_payload = {
    }

    response = requests.post(url = f'{qmoney_url}/verifyCode', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == -20002
    assert json_response['responseMessage'] == 'Mandatory parmater missing : transactionId'

  def test_failing_at_confirming_transaction_when_wrong_transaction_id(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    before_initiating_transaction = datetime.now(tz = timezone(timedelta(hours = 1)))

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'OTP Send Successfully'
    assert json_response['data']['transactionId'] is not None

    gmail = Gmail()

    mustend = time.time() + 300

    messages = []
    while time.time() < mustend and len(messages) == 0:
      messages = gmail.get_messages(query=construct_query(unread=True, sender='alerts@qmoney.gm', subject='Otp - QCell', newer_than=(1, 'day')))
      messages.sort(key=lambda msg: msg.date)
      time.sleep(5)

    assert len(messages) > 0, 'No new email message with the sent OTP found'
    [message.mark_as_read() for message in messages]

    message = messages[-1]
    assert datetime.fromisoformat(message.date) > before_initiating_transaction, 'the date of the message is earlier than the time the request has been made'
    match = re.search(r"Generated OTP : \d+", message.html)

    assert match is not None, 'No OTP found in the most recent retrieved email'

    otp = match.group(0).replace('Generated OTP : ', '')

    json_payload = {
      'transactionId': 'transactionId',
      'otp': otp 
    }

    response = requests.post(url = f'{qmoney_url}/verifyCode', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == -150001
    assert json_response['responseMessage'] == 'Adapter Session Not Found session id : transactionId event : CLIENT_ADAPTER_VERIFYOTP_REQUEST '

  def test_failing_at_confirming_transaction_when_wrong_otp_or_missing_otp(self, qmoney_url, qmoney_credentials, qmoney_token, qmoney_getmoney_json_payload):
    access_token = self.login(qmoney_url, qmoney_credentials, qmoney_token)
    json_payload = qmoney_getmoney_json_payload

    before_initiating_transaction = datetime.now(tz = timezone(timedelta(hours = 1)))

    response = requests.post(url = f'{qmoney_url}/getMoney', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '1'
    assert json_response['responseMessage'] == 'OTP Send Successfully'
    assert json_response['data']['transactionId'] is not None

    transaction_id = json_response['data']['transactionId']

    json_payload = {
      'transactionId': transaction_id,
      'otp': 'otp'
    }

    response = requests.post(url = f'{qmoney_url}/verifyCode', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '-150005'
    assert json_response['responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'

    json_payload = {
      'transactionId': transaction_id
    }

    response = requests.post(url = f'{qmoney_url}/verifyCode', json = json_payload, auth = QMoneyBearerAuth(access_token))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['responseCode'] == '-150005'
    assert json_response['responseMessage'] == f'Two factor OTP validation fail for transactionId : {transaction_id}'