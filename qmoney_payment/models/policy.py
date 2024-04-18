from .utils import get_openimis_model


def get_policy_model():
    return get_openimis_model('policy', 'Policy')


def is_from_policy_app():
    return get_policy_model()._meta.app_label == 'policy'


def get_fully_qualified_name_of_policy_model():
    model = get_policy_model()
    return f'{model._meta.app_label}.{model._meta.model_name}'


STATUS_NAME = {
    1: 'idle',
    2: 'active',
    4: 'suspended',
    8: 'expired',
    16: 'ready'
}


def status_to_string(status):
    return STATUS_NAME.get(status, 'unknown')