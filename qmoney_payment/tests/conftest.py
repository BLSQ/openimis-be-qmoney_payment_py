import os
import pytest
import time

from simplegmail import Gmail

from helpers import QMoney, gmail_mark_as_read_recent_emails_with_qmoney_otp


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "amount_to_pay(amount): use internally to pass data to some tests")
    config.addinivalue_line(
        "markers", "with_gmail: run tests relying on a GMail account")


@pytest.fixture(scope='session')
def qmoney_url():
    return os.getenv('QMONEY_URL')


@pytest.fixture(scope='session')
def qmoney_credentials():
    return (os.getenv('QMONEY_USERNAME'), os.getenv('QMONEY_PASSWORD'))


@pytest.fixture(scope='session')
def qmoney_token():
    return os.getenv('QMONEY_TOKEN')


@pytest.fixture(scope='session')
def qmoney_payer():
    return os.getenv('QMONEY_PAYER')


@pytest.fixture(scope='session')
def qmoney_payee():
    return os.getenv('QMONEY_PAYEE')


@pytest.fixture(scope='session')
def qmoney_payee_pin_code():
    return os.getenv('QMONEY_PAYEE_PIN_CODE')


@pytest.fixture(scope='function')
def qmoney_getmoney_json_payload():
    return {
        'data': {
            'fromUser': {
                'userIdentifier': os.getenv('QMONEY_PAYER'),
            },
            'toUser': {
                'userIdentifier': os.getenv('QMONEY_PAYEE'),
            },
            'serviceId': 'MOBILE_MONEY',
            'productId': 'NHIA_GETMONEY',
            'remarks': 'add',
            'payment': [
                {
                    'amount': 1
                },
            ],
            'transactionPin': os.getenv('QMONEY_PAYEE_PIN_CODE')
        }
    }.copy()


@pytest.fixture(scope='class')
def qmoney_access_token(qmoney_url, qmoney_credentials, qmoney_token):
    return QMoney.login(qmoney_url, qmoney_credentials, qmoney_token)


@pytest.fixture(scope='class')
def gmail_client():
    client = Gmail()
    time.sleep(5)
    gmail_mark_as_read_recent_emails_with_qmoney_otp(client)
    yield client
    gmail_mark_as_read_recent_emails_with_qmoney_otp(client)
