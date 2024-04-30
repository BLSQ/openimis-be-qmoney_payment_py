import os

from django.apps import AppConfig, apps

from qmoney_payment.api.client import Client as QMoneyClient
import qmoney_payment.env

DEFAULT_CONFIG = {
    'gql_qmoney_payment_get_permissions': ['207000'],
    'gql_qmoney_payment_list_permissions': ['207001'],
    'gql_qmoney_payment_request_permissions': ['207002'],
    'gql_qmoney_payment_proceed_permissions': ['207003']
}


class QMoneyPaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'qmoney_payment'
    session = None
    merchant = None
    gql_qmoney_payment_get_permissions = []
    gql_qmoney_payment_list_permissions = []
    gql_qmoney_payment_request_permissions = []
    gql_qmoney_payment_proceed_permissions = []

    def __init__(self, app_name, app_module):
        qmoney_payment.env.load_env()
        super().__init__(app_name, app_module)
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

    def get_gql_permission_for(self, action):
        return getattr(self, f'gql_qmoney_payment_{action}_permissions')

    @classmethod
    def __load_config(cls):
        config = cls.__get_default_config_or_from_database()
        for field in config:
            if hasattr(QMoneyPaymentConfig, field):
                setattr(QMoneyPaymentConfig, field, config[field])

    @classmethod
    def __get_default_config_or_from_database(cls):
        try:
            module_configuration_model = apps.get_model('core',
                                                        'ModuleConfiguration',
                                                        require_ready=False)
            return module_configuration_model.get_or_default(
                cls.name, DEFAULT_CONFIG)
        except LookupError:
            return DEFAULT_CONFIG

    def ready(self):
        self.__load_config()
        if self.session is None:
            self.session = QMoneyClient.session(self.settings['url'],
                                                self.settings['username'],
                                                self.settings['password'],
                                                self.settings['token'])
        if self.merchant is None:
            self.merchant = self.session.merchant(
                self.settings['merchant_wallet'],
                self.settings['merchant_pincode'])