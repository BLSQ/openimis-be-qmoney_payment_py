from django.db import connection
from qmoney_payment.models.policy import Policy

# The project tests can be run either independently or with the OpenIMIS test
# harness. The latter will set up the database, including performing the
# migrations and creating the schema. When running independently, the DB
# schemas of the managed models are those created by Django. To avoid too much
# coupling, we have some models that are partial definitions of existing models
# defined in other modules. These models are unmanaged, i.e. Django does not
# create their corresponding DB schema. The present helpers allow you to do
# that for the Policy model.


def setup_policy_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Policy)
    connection.enable_constraint_checking()


def teardown_policy_table():
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(Policy)
    connection.enable_constraint_checking()
