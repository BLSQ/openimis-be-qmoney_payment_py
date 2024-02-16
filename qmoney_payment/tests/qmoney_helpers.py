import os
import qmoney_payment.env

from .helpers import QMoney


def qmoney_url():
    qmoney_payment.env.load_env()
    return os.getenv('QMONEY_URL')


def qmoney_credentials():
    qmoney_payment.env.load_env()
    return (os.getenv('QMONEY_USERNAME'), os.getenv('QMONEY_PASSWORD'))


def qmoney_token():
    qmoney_payment.env.load_env()
    return os.getenv('QMONEY_TOKEN')


def qmoney_payer():
    qmoney_payment.env.load_env()
    return os.getenv('QMONEY_PAYER')


def qmoney_payee():
    qmoney_payment.env.load_env()
    return os.getenv('QMONEY_PAYEE')


def qmoney_payee_pin_code():
    qmoney_payment.env.load_env()
    return os.getenv('QMONEY_PAYEE_PIN_CODE')


def qmoney_access_token():
    qmoney_payment.env.load_env()
    return QMoney.login(qmoney_url(), qmoney_credentials(), qmoney_token())


def qmoney_getmoney_json_payload():
    return {
        'data': {
            'fromUser': {
                'userIdentifier': qmoney_payer(),
            },
            'toUser': {
                'userIdentifier': qmoney_payee(),
            },
            'serviceId': 'MOBILE_MONEY',
            'productId': 'NHIA_GETMONEY',
            'remarks': 'add',
            'payment': [
                {
                    'amount': 1
                },
            ],
            'transactionPin': qmoney_payee_pin_code()
        }
    }.copy()