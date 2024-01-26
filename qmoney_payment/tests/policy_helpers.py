from django.db import connection
from qmoney_payment.models.policy import Policy


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
