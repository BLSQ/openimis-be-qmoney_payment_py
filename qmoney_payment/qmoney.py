from enum import Enum
import logging
import requests

logger = logging.getLogger(__name__)


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


class PaymentTransaction:
    to_merchant = None
    from_wallet_id = None
    amount_to_pay = 0
    session = None
    transaction_id = None
    State = Enum('State',
                 ['INITIATED', 'WAITING_FOR_CONFIRMATION', 'PROCEEDED'])
    current_state = State.INITIATED

    def __init__(self, with_session, to_merchant, from_wallet_id, amount):
        self.to_merchant = to_merchant
        self.from_wallet_id = from_wallet_id
        self.amount_to_pay = amount
        self.session = with_session

    def state(self):
        return self.current_state

    def amount(self):
        return self.amount_to_pay

    def payer(self):
        return self.from_wallet_id

    def merchant(self):
        return self.to_merchant

    def request_otp(self):
        transaction_id = self.session.get_money(self.from_wallet_id,
                                                self.to_merchant.wallet_id,
                                                self.amount_to_pay,
                                                self.to_merchant.pin_code)

        if transaction_id is not None:
            self.current_state = PaymentTransaction.State.WAITING_FOR_CONFIRMATION
            self.transaction_id = transaction_id

        return transaction_id != None

    def proceed(self, otp):
        if self.transaction_id is None:
            return (
                False,
                'There isn\'t a transaction ID associated to this payment. Please request one before.'
            )
        if otp is None:
            return (False, 'The provided OTP is empty.')
        result = self.session.verify_code(self.transaction_id, otp)
        if result[0]:
            self.current_state = PaymentTransaction.State.PROCEEDED
        return result


class Merchant:
    wallet_id = None
    pin_code = None

    def __init__(self, wallet_id, pin_code):
        self.wallet_id = wallet_id
        self.pin_code = pin_code

    def request_payment(self, session, from_wallet_id, amount):
        payment_transaction = PaymentTransaction(session, self, from_wallet_id,
                                                 amount)
        payment_transaction.request_otp()
        return payment_transaction


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
        self.login()

    def login(self):
        json_payload = {
            'grantType': 'password',
            'username': self.username,
            'password': self.password,
        }
        response = requests.post(url=f'{self.url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(self.login_token))

        self.access_token = response.json()['data']['access_token']

    @classmethod
    def service_name(cls):
        return 'MOBILE_MONEY'

    @classmethod
    def product_name(cls):
        return 'NHIA_GETMONEY'

    def get_money(self, payer_wallet_id, merchant_wallet_id, amount,
                  merchant_pin_code):
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
                                 auth=QMoneyBearerAuth(self.access_token))

        logger.debug('POST /getMoney response:\n%s', response.text)

        if response.status_code != 200 or response.json(
        )['responseCode'] != '1':
            return None
        return response.json()['data']['transactionId']

    def verify_code(self, transaction_id, otp):
        payload = {'transactionId': transaction_id, 'otp': otp}

        logger.debug('POST /verifyCode with payload:\n%s', payload)
        response = requests.post(url=f'{self.url}/verifyCode',
                                 json=payload,
                                 auth=QMoneyBearerAuth(self.access_token))
        logger.debug('POST /verifyCode response:\n%s', response.text)

        if response.status_code != 200 or response.json(
        )['responseCode'] != '1':
            return (False, response.text)

        return (True, response.text)

    def merchant(self, merchant_wallet_id, pin_code):
        return Merchant(merchant_wallet_id, pin_code)


class QMoney:

    @classmethod
    def session(cls, url, username, password, login_token):
        return Session(url, username, password, login_token)
