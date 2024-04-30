import uuid

from django.apps import apps
from django.core.validators import MinValueValidator, ValidationError
from django.db import models
from django.db.models import Count, Q
# from django.db import transaction as django_db_transaction
from django.utils.translation import gettext as _

from qmoney_payment.apps import QMoneyPaymentConfig
from qmoney_payment.api.payment_transaction import PaymentTransaction
from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model


class QMoneyPayment(models.Model):

    MAX_SIMULTANEOUS_UNPROCEEDED_TRANSACTIONS = 1

    Status = models.TextChoices('Status',
                                [(elem.name[0], elem.name)
                                 for elem in PaymentTransaction.State])

    uuid = models.UUIDField(primary_key=True,
                            default=uuid.uuid4,
                            editable=False)
    policy = models.ForeignKey(
        get_policy_model(),
        on_delete=models.CASCADE,
        # probably to enforce
        blank=True,
        null=True)
    premium = models.ForeignKey(get_premium_model(),
                                on_delete=models.CASCADE,
                                blank=True,
                                null=True)
    external_transaction_id = models.CharField(max_length=200,
                                               null=True,
                                               blank=True)
    status = models.CharField(choices=Status.choices,
                              default=Status.I,
                              max_length=32)
    transaction = None

    # TODO Decide the precision: unity, dime, centime
    amount = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    payer_wallet = models.CharField(max_length=200)

    @property
    def policy_uuid(self):
        if self.policy is None:
            return None
        return self.policy.uuid

    @property
    def premium_uuid(self):
        if self.premium is None:
            return None
        return self.premium.uuid

    def is_canceled(self):
        return self.status == QMoneyPayment.Status.C

    def is_waiting_for_confirmation(self):
        return self.status == QMoneyPayment.Status.W

    def is_proceeded(self):
        return self.status == QMoneyPayment.Status.P

    def is_initiated(self):
        return self.status == QMoneyPayment.Status.I

    def set_status_after_cancel(self):
        self.status = QMoneyPayment.Status.C
        self.save()

    def set_status_after_request(self, transaction):
        self.transaction = transaction

        if not transaction.is_waiting_for_confirmation():
            self.status = QMoneyPayment.Status.F
            self.save()
            return False

        self.status = QMoneyPayment.Status.W
        self.external_transaction_id = transaction.transaction_id
        self.save()
        return True

    def set_status_after_proceed(self):
        self.status = QMoneyPayment.Status.P
        self.save()

    def is_policy_idle(self):
        return self.policy.status is not get_policy_model().STATUS_IDLE

    def payment_transaction(self):
        if self.transaction is not None:
            return self.transaction
        config = apps.get_app_config(QMoneyPaymentConfig.name)
        self.transaction = PaymentTransaction(config.session, config.merchant,
                                              self.payer_wallet, self.amount,
                                              self.status,
                                              self.external_transaction_id)
        return self.transaction

    def save(self, *args, **kwargs):
        if self.policy is not None and self.status != QMoneyPayment.Status.C:
            policy_from_db = get_policy_model(
            ).objects.filter(id=self.policy.id).annotate(
                ongoing_unproceeded_transactions=Count(
                    'qmoneypayment__policy__pk',
                    filter=~Q(qmoneypayment__status__exact=self.Status.P)
                    & ~Q(qmoneypayment__status__exact=self.Status.C))).first()
            max_unproceeded_transactions = self.MAX_SIMULTANEOUS_UNPROCEEDED_TRANSACTIONS
            if not self._state.adding:
                max_unproceeded_transactions += 1
            if policy_from_db is not None and policy_from_db.ongoing_unproceeded_transactions >= max_unproceeded_transactions:
                raise ValidationError(
                    # Translators: This message will replace named-string max
                    _('models.qmoney_payment.save.error.validation.maximum_transactions_reached'
                      ).format(
                          max=self.MAX_SIMULTANEOUS_UNPROCEEDED_TRANSACTIONS))
        self.transaction = None
        return super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'tblQmoneyPayment'
        app_label = 'qmoney_payment'
