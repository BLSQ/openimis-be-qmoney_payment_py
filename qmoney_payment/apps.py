import os

from django.apps import AppConfig

from qmoney_payment.qmoney import QMoney
import qmoney_payment.env


class QMoneyPaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qmoney_payment'
    session = None
    merchant = None

    def __init__(self, app_name, app_module):
        qmoney_payment.env.load_env()
        super(QMoneyPaymentConfig, self).__init__(app_name, app_module)
        self.settings = {
            'url': os.getenv('QMONEY_URL'),
            'username': os.getenv('QMONEY_USERNAME'),
            'password': os.getenv('QMONEY_PASSWORD'),
            'token': os.getenv('QMONEY_TOKEN'),
            'merchant_wallet': os.getenv('QMONEY_PAYEE'),
            'merchant_pincode': os.getenv('QMONEY_PAYEE_PIN_CODE'),
        }
        self.session = None
        self.merchant = None

    def ready(self):
        if self.session is None:
            self.session = QMoney.session(self.settings['url'],
                                          self.settings['username'],
                                          self.settings['password'],
                                          self.settings['token'])
        if self.merchant is None:
            self.merchant = self.session.merchant(
                self.settings['merchant_wallet'],
                self.settings['merchant_pincode'])