from django.db import models


class FakeMutationLog(models.Model):
    RECEIVED = 0
    ERROR = 1
    SUCCESS = 2
    STATUS_CHOICES = (
        (RECEIVED, "Received"),
        (ERROR, "Error"),
        (SUCCESS, "Success"),
    )

    id = models.AutoField(db_column='PolicyID', primary_key=True)
    user_id = models.IntegerField(blank=True, null=True)
    json_content = models.TextField()
    client_mutation_label = models.CharField(max_length=255,
                                             blank=True,
                                             null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=RECEIVED)
    error = models.TextField(blank=True, null=True)

    def mark_as_successful(self):
        if self.status != self.RECEIVED:
            return

        self.status = self.SUCCESS
        self.save()

    def mark_as_failed(self, errors_json):
        self.status = self.ERROR
        self.error = errors_json
        self.save()

    class Meta:
        managed = False
        db_table = 'core_Mutation_Log'
        app_label = 'qmoneyPayments'
