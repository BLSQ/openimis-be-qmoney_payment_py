from django.db import connection


def setup_table_for(model):
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(model)
    connection.enable_constraint_checking()


def teardown_table_for(model):
    connection.disable_constraint_checking()
    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(model)
    connection.enable_constraint_checking()