import uuid

from django.apps import apps
from django.db import models

from qmoney_payment.models.policy import get_policy_model


class Premium(models.Model):
    id = models.AutoField(db_column="PremiumId", primary_key=True)
    uuid = models.CharField(db_column="PremiumUUID",
                            max_length=36,
                            default=uuid.uuid4,
                            unique=True)

    policy = models.ForeignKey(get_policy_model(),
                               models.DO_NOTHING,
                               db_column="PolicyID",
                               related_name="qmoney_payment")

    amount = models.DecimalField(db_column="Amount",
                                 max_digits=18,
                                 decimal_places=2)
    receipt = models.CharField(db_column="Receipt", max_length=50)
    pay_type = models.CharField(db_column="PayType", max_length=1)
    pay_date = models.DateField(db_column="PayDate")
    is_offline = models.BooleanField(db_column="isOffline",
                                     blank=True,
                                     null=True,
                                     default=False)

    class Meta:
        managed = False
        db_table = 'tblPremium'
        app_label = 'qmoney_payment'


def get_premium_model():
    try:
        model = apps.get_model('contribution', 'Premium', require_ready=False)
        return model
    except LookupError as _:
        return Premium


def is_from_premium_app():
    return get_premium_model()._meta.app_label == 'contribution'


def get_fully_qualified_name_of_premium_model():
    model = get_premium_model()
    return f'{model._meta.app_label}.{model._meta.model_name}'