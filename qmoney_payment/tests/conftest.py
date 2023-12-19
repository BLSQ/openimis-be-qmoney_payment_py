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