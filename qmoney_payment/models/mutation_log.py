from .utils import get_openimis_model, is_from_app, get_fully_qualified_name_of_model

APP_NAME = 'core'
MODEL_NAME = 'MutationLog'


def get_mutation_log_model():
    return get_openimis_model(APP_NAME, MODEL_NAME)


def is_from_mutation_log_app():
    return is_from_app(get_mutation_log_model(), APP_NAME)


def get_fully_qualified_name_of_mutation_log_model():
    return get_fully_qualified_name_of_model(get_mutation_log_model())
