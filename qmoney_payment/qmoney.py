from enum import Enum
import logging
import requests

from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

TIMEOUT = 100


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
    State = Enum('State', [
        'INITIATED', 'WAITING_FOR_CONFIRMATION', 'PROCEEDED', 'UNKNOWN',
        'FAILED', 'CANCELED'
    ])
    current_state = State.UNKNOWN

    def __init__(  # pylint: disable=too-many-arguments
            self,
            with_session,
            to_merchant,
            from_wallet_id,
            amount,
            state_initial='I',
            assigned_transaction_id=None):
        self.to_merchant = to_merchant
        self.from_wallet_id = from_wallet_id
        self.amount_to_pay = amount
        self.session = with_session
        self.transaction_id = assigned_transaction_id
        self.current_state = self.__convert_state_initial_to_state_enum(
            state_initial)

    def __convert_state_initial_to_state_enum(self, state_initial):
        return next(
            iter([
                elem for elem in PaymentTransaction.State
                if state_initial in (elem.name[0], elem.name)
            ]), PaymentTransaction.State.UNKNOWN)

    def is_initiated(self):
        return self.current_state == PaymentTransaction.State.INITIATED

    def is_waiting_for_confirmation(self):
        return self.current_state == PaymentTransaction.State.WAITING_FOR_CONFIRMATION

    def is_proceeded(self):
        return self.current_state == PaymentTransaction.State.PROCEEDED

    def is_failed(self):
        return self.current_state == PaymentTransaction.State.FAILED

    def is_in_unknown_state(self):
        return self.current_state == PaymentTransaction.State.UNKNOWN

    def is_canceled(self):
        return self.current_state == PaymentTransaction.State.CANCELED

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
        else:
            self.current_state = PaymentTransaction.State.FAILED

        return transaction_id is not None

    def proceed(self, otp):
        if self.transaction_id is None:
            return False, _('qmoney_payment.proceed.error.transaction_empty')
        if otp is None:
            return False, _('qmoney_payment.proceed.error.otp_empty')
        result = self.session.verify_code(self.transaction_id, otp)
        if result[0]:
            self.current_state = PaymentTransaction.State.PROCEEDED
        else:
            self.current_state = PaymentTransaction.State.FAILED
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


class QMoney:

    @classmethod
    def session(cls, url, username, password, login_token):
        return Session(url, username, password, login_token)
