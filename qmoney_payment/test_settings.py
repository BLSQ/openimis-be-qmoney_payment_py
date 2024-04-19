DATABASES = {}
DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': 'db.sqlite3'
}
USE_TZ = False
INSTALLED_APPS = [
    'qmoney_payment', 'django.contrib.auth', 'django.contrib.contenttypes'
]
SITE_ROOT = 'api/'

LANGUAGE_CODE = 'en'

LOCALE_PATHS = ['locale']

CUSTOM_MODELS = {
    'Policy': ('qmoney_payment.tests.policy_helpers', 'FakePolicy'),
    'Premium': ('qmoney_payment.tests.premium_helpers', 'FakePremium')
}