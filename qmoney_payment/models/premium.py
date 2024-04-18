from qmoney_payment.models.policy import get_policy_model
from .utils import get_openimis_model


def get_premium_model():
    return get_openimis_model('contribution', 'Premium')


def is_from_premium_app():
    return get_premium_model()._meta.app_label == 'contribution'


def get_fully_qualified_name_of_premium_model():
    model = get_premium_model()
    return f'{model._meta.app_label}.{model._meta.model_name}'