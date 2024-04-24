import os
import sys

DOTENV = {'loaded': False, 'file': None, 'environment': None}


def is_test_environment():
    return sys.argv[1:2] == [
        'test'
    ] or 'PYTEST_CURRENT_TEST' in os.environ or os.environ.get(
        'DJANGO_SETTINGS_MODULE', '') == 'qmoney_payment.test_settings'


def load_env():
    if not DOTENV['loaded']:
        from dotenv import load_dotenv  # pylint: disable=import-outside-toplevel
        if is_test_environment():
            DOTENV['file'] = '.test.env'
            DOTENV['environment'] = 'test'
            load_dotenv('.test.env')
            DOTENV['loaded'] = True
        else:
            DOTENV['file'] = '.env'
            DOTENV['environment'] = 'prod'
            load_dotenv('.env')
            DOTENV['loaded'] = False
