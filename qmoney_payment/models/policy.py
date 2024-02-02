import uuid

from django.db import models


class Policy(models.Model):
    STATUS_IDLE = 1
    STATUS_ACTIVE = 2
    STATUS_SUSPENDED = 4
    STATUS_EXPIRED = 8
    STATUS_READY = 16
    uuid = models.UUIDField(db_column='PolicyUUID',
                            max_length=36,
                            default=uuid.uuid4,
                            unique=True)
    status = models.SmallIntegerField(db_column='PolicyStatus',
                                      blank=True,
                                      null=True)

    class Meta:
        managed = False
        db_table = 'tblPolicy'