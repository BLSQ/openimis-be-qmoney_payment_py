import uuid

from django.db import models


class Policy(models.Model):
  uuid = models.UUIDField(db_column='PolicyUUID',
                          max_length=36,
                          default=uuid.uuid4,
                          unique=True)

  class Meta:
    managed = False
    db_table = 'tblPolicy'