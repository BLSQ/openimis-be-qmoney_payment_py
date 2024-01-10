import requests

from simplegmail.query import construct_query


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


class QMoney:

  @classmethod
  def service_name(cls):
    return 'MOBILE_MONEY'

  @classmethod
  def product_name(cls):
    return 'NHIA_GETMONEY'

  @classmethod
  def login(cls, url, credentials, token, raw=False):
    json_payload = {
        'grantType': 'password',
        'username': credentials[0],
        'password': credentials[1],
    }
    response = requests.post(url=f'{url}/login',
                             json=json_payload,
                             auth=QMoneyBasicAuth(token))
    if raw:
      return response
    return response.json()['data']['access_token']

  @classmethod
  def initiate_transaction(cls, url, access_token, payer, payee, amount,
                           pin_code):
    payload = {
        'data': {
            'fromUser': {
                'userIdentifier': payer,
            },
            'toUser': {
                'userIdentifier': payee,
            },
            'serviceId': cls.service_name(),
            'productId': cls.product_name(),
            'remarks': 'add',
            'payment': [
                {
                    'amount': amount
                },
            ],
            'transactionPin': pin_code
        }
    }

    return requests.post(url=f'{url}/getMoney',
                         json=payload,
                         auth=QMoneyBearerAuth(access_token))

  @classmethod
  def proceed_transaction(cls, url, access_token, transaction_id, otp):
    payload = {'transactionId': transaction_id, 'otp': otp}

    if transaction_id is None:
      del payload['transactionId']

    if otp is None:
      del payload['otp']

    return requests.post(url=f'{url}/verifyCode',
                         json=payload,
                         auth=QMoneyBearerAuth(access_token))


def get_from(the_map, keys):
  if the_map is None or len(the_map) == 0:
    return None
  if keys is None or len(keys) == 0:
    return None
  if len(keys) == 1:
    return the_map.get(keys[0], None)
  return get_from(the_map[keys[0]], keys[1:])


def del_from(the_map, keys):
  if the_map is None or len(the_map) == 0:
    return None
  if keys is None or len(keys) == 0:
    return None
  if len(keys) == 1:
    del the_map[keys[0]]
  else:
    del_from(the_map[keys[0]], keys[1:])
  return the_map


def set_into(the_map, keys, value):
  if the_map is None:
    return None
  if keys is None or len(keys) == 0:
    return None
  if len(keys) == 1:
    the_map[keys[0]] = value
  else:
    set_into(the_map[keys[0]], keys[1:], value)
  return the_map


def gmail_query_of_recent_emails_with_qmoney_otp():
  return construct_query(unread=True,
                         sender='alerts@qmoney.gm',
                         subject='Otp - QCell',
                         newer_than=(1, 'day'))


def gmail_get_recent_emails_with_qmoney_otp(client):
  return client.get_messages(
      query=gmail_query_of_recent_emails_with_qmoney_otp())


def gmail_mark_as_read_recent_emails_with_qmoney_otp(client):
  messages = gmail_get_recent_emails_with_qmoney_otp(client)
  [message.mark_as_read() for message in messages]