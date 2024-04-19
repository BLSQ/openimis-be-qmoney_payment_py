import uuid

from django.conf import settings
from django.db import connection
from django.db import models

# The project tests can be run either independently or with the OpenIMIS test
# harness. The latter will set up the database, including performing the
# migrations and creating the schema. When running independently, the DB
# schemas of the managed models are those created by Django. To avoid too much
# coupling, we have some models that are partial definitions of existing models
# defined in other modules. These models are unmanaged, i.e. Django does not
# create their corresponding DB schema. The present helpers allow you to do
# that for the Policy model.


class FakePolicy(models.Model):
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


def setup_policy_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(FakePolicy)
    connection.enable_constraint_checking()


def teardown_policy_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(FakePolicy)
    connection.enable_constraint_checking()
