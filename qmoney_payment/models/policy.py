import uuid

from django.apps import apps
from django.db import models


class Policy(models.Model):
    STATUS_IDLE = 1
    STATUS_ACTIVE = 2
    STATUS_SUSPENDED = 4
    STATUS_EXPIRED = 8
    STATUS_READY = 16
    id = models.AutoField(db_column='PolicyID', primary_key=True)
    uuid = models.CharField(db_column='PolicyUUID',
                            max_length=36,
                            default=uuid.uuid4,
                            unique=True)
    status = models.SmallIntegerField(db_column='PolicyStatus',
                                      blank=True,
                                      null=True)

    class Meta:
        managed = False
        db_table = 'tblPolicy'
        app_label = 'qmoney_payment'


def get_policy_model():
    try:
        model = apps.get_model('policy', 'Policy', require_ready=False)
        return model
    except LookupError as _:
        return Policy


def is_from_policy_app():
    return get_policy_model()._meta.app_label == 'policy'


def get_fully_qualified_name_of_policy_model():
    model = get_policy_model()
    return f'{model._meta.app_label}.{model._meta.model_name}'