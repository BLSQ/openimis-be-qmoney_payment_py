import uuid

from django.db import connection
from django.db import models
from qmoney_payment.models.policy import get_policy_model

# The project tests can be run either independently or with the OpenIMIS test
# harness. The latter will set up the database, including performing the
# migrations and creating the schema. When running independently, the DB
# schemas of the managed models are those created by Django. To avoid too much
# coupling, we have some models that are partial definitions of existing models
# defined in other modules. These models are unmanaged, i.e. Django does not
# create their corresponding DB schema. The present helpers allow you to do
# that for the Premium model.


class FakePremium(models.Model):
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


def setup_premium_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(FakePremium)
    connection.enable_constraint_checking()


def teardown_premium_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(FakePremium)
    connection.enable_constraint_checking()
