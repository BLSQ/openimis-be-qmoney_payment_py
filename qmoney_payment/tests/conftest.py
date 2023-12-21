import os
import pytest

@pytest.fixture(scope="session")
def qmoney_url():
  return os.getenv('QMONEY_URL', 'https://uat-adpelite.qmoney.gm')

@pytest.fixture(scope="session")
def qmoney_credentials():
  return (
    os.getenv('QMONEY_USERNAME'),
    os.getenv('QMONEY_PASSWORD')
  )

@pytest.fixture(scope="session")
def qmoney_token():
  return os.getenv('QMONEY_TOKEN')

@pytest.fixture(scope="function")
def qmoney_getmoney_json_payload():
  return {
      'data': {
        'fromUser': {
          'userIdentifier': '5811724c',
        },
        'toUser': {
          'userIdentifier': '14001502'
        },
        'serviceId': 'MOBILE_MONEY',
        'productId': 'NHIA_GETMONEY',
        'remarks': 'add',
        'payment': [
          {'amount': 1},
        ],
        'transactionPin': '1234'
      }
    }.copy()