from .utils import get_openimis_model, is_from_app, get_fully_qualified_name_of_model

APP_NAME = 'policy'
MODEL_NAME = 'Policy'


def get_policy_model():
    return get_openimis_model(APP_NAME, MODEL_NAME)


def is_from_policy_app():
    return is_from_app(get_policy_model(), APP_NAME)


def get_fully_qualified_name_of_policy_model():
    return get_fully_qualified_name_of_model(get_policy_model())


STATUS_NAME = {
    1: 'idle',
    2: 'active',
    4: 'suspended',
    8: 'expired',
    16: 'ready'
}


def status_to_string(status):
    return STATUS_NAME.get(status, 'unknown')