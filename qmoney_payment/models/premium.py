from .utils import get_openimis_model, is_from_app, get_fully_qualified_name_of_model

APP_NAME = 'contribution'
MODEL_NAME = 'Premium'


def get_premium_model():
    return get_openimis_model(APP_NAME, MODEL_NAME)


def is_from_premium_app():
    return is_from_app(get_premium_model(), APP_NAME)


def get_fully_qualified_name_of_premium_model():
    return get_fully_qualified_name_of_model(get_premium_model())