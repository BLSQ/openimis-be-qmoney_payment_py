from django.apps import apps
from django.conf import settings


def import_class(from_module, name):
    import importlib

    module = importlib.import_module(f'{from_module}')
    return getattr(module, name)


def get_openimis_model(openimis_module, name):
    try:
        model = apps.get_model(openimis_module, name, require_ready=False)
        return model
    except LookupError as _:
        model_fqn = settings.CUSTOM_MODELS.get(
            name, None) if settings.CUSTOM_MODELS is not None else None
        if model_fqn is None:
            raise LookupError(
                f'A custom model for {name} has not been set up. Please provide one in settings.'
            )
        model = import_class(model_fqn[0], model_fqn[1])
        return model