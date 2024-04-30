import logging
import requests

from .auth_base import QMoneyBasicAuth, QMoneyBearerAuth
from .merchant import Merchant

logger = logging.getLogger(__name__)

TIMEOUT = 100


class Session:
    url = None
    username = None
    password = None
    login_token = None
    access_token = None

    def __init__(self, url, username, password, login_token):
        self.url = url
        self.username = username
        self.password = password
        self.login_token = login_token

    def is_logged_in(self):
        return self.access_token is not None

    def login(self):
        if self.is_logged_in():
            return
        json_payload = {
            'grantType': 'password',
            'username': self.username,
            'password': self.password,
        }
        response = requests.post(url=f'{self.url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(self.login_token),
                                 timeout=TIMEOUT)

        self.access_token = response.json()['data']['access_token']

    @classmethod
    def service_name(cls):
        return 'MOBILE_MONEY'

    @classmethod
    def product_name(cls):
        return 'NHIA_GETMONEY'

    def get_money(self, payer_wallet_id, merchant_wallet_id, amount,
                  merchant_pin_code):
        self.login()
        payload = {
            'data': {
                'fromUser': {
                    'userIdentifier': payer_wallet_id,
                },
                'toUser': {
                    'userIdentifier': merchant_wallet_id,
                },
                'serviceId': self.service_name(),
                'productId': self.product_name(),
                'remarks': 'add',
                'payment': [
                    {
                        'amount': amount
                    },
                ],
                'transactionPin': merchant_pin_code
            }
        }
        logger.debug('POST /getMoney with payload:\n%s', payload)

        response = requests.post(url=f'{self.url}/getMoney',
                                 json=payload,
                                 auth=QMoneyBearerAuth(self.access_token),
                                 timeout=TIMEOUT)

        logger.debug('POST /getMoney response:\n%s', response.text)

        if response.status_code != 200 or response.json(
        )['responseCode'] != '1':
            return None
        return response.json()['data']['transactionId']

    def verify_code(self, transaction_id, otp):
        self.login()
        payload = {'transactionId': transaction_id, 'otp': otp}

        logger.debug('POST /verifyCode with payload:\n%s', payload)
        response = requests.post(url=f'{self.url}/verifyCode',
                                 json=payload,
                                 auth=QMoneyBearerAuth(self.access_token),
                                 timeout=TIMEOUT)
        logger.debug('POST /verifyCode response:\n%s', response.text)

        if response.status_code != 200 or response.json(
        )['responseCode'] != '1':
            return (False, response.text)

        return (True, response.text)

    def merchant(self, merchant_wallet_id, pin_code):
        return Merchant(merchant_wallet_id, pin_code)
