import uuid

from django.apps import apps
from django.core.validators import MinValueValidator
from django.db import models
from django.db import transaction as django_db_transaction

from qmoney_payment.apps import QMoneyPaymentConfig
from qmoney_payment.qmoney import PaymentTransaction
from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model
from qmoney_payment.services import create_premium_for

Struct = lambda **kwargs: type("Object", (), kwargs)


class QMoneyPayment(models.Model):

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

    def is_proceeded(self):
        return self.status == QMoneyPayment.Status.P

    def request(self):
        if self.payment_transaction().is_waiting_for_confirmation():
            # Should probably not happen as the object is always created by the
            # mutation before requesting
            return {'ok': True, 'status': self.status}
        if self.payment_transaction().is_proceeded():
            # Should probably not happen as the object is always created by the
            # mutation before requesting
            return {
                'ok': False,
                'status': self.status,
                'message': 'The payment has already been proceeded.'
            }
        if self.policy.status is not get_policy_model().STATUS_IDLE:
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                f'The Policy {self.policy_uuid} should be Idle but it is not.'
            }

        # TODO manage the case the object has already been created, reuse ?
        self.transaction = self.merchant().request_payment(
            self.session(), self.payer_wallet, self.amount)
        if self.payment_transaction().is_waiting_for_confirmation():
            self.status = QMoneyPayment.Status.W
            self.external_transaction_id = self.transaction.transaction_id
            self.save()
        else:
            # TODO to manage, buuuuut except network error, it should be always ok due to the API :/
            # maybe with the get transaction state of their API ?
            self.status = QMoneyPayment.Status.F
            return {
                'ok': False,
                'status': self.status,
                'message': 'The request could not have been made.',
                # Add more details
            }
        return {'ok': True, 'status': self.status}

    @django_db_transaction.atomic
    def proceed(self, otp, user):
        if self.payment_transaction().is_proceeded():
            # maybe "raise an info" to say it's already done
            return {'ok': True, 'status': self.status}
        if self.payment_transaction().is_initiated():
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                'The payment has not been requested. Please request it first before proceeding it.'
            }

        # TODO manage the case the object has already been created, reuse ?
        response = self.payment_transaction().proceed(otp)
        if response[0]:
            self.status = QMoneyPayment.Status.P
            self.save()
            create_premium_for(self, user)
        else:
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                f'The payment failed due to the following reason: {response[1]}',
                # Add more details
            }
        return {'ok': True, 'status': self.status}

    def merchant(self):
        config = apps.get_app_config(QMoneyPaymentConfig.name)
        return config.merchant

    def session(self):
        config = apps.get_app_config(QMoneyPaymentConfig.name)
        return config.session

    def payment_transaction(self):
        if self.transaction is not None:
            return self.transaction
        self.transaction = PaymentTransaction(self.session(), self.merchant(),
                                              self.payer_wallet, self.amount,
                                              self.status,
                                              self.external_transaction_id)
        return self.transaction

    class Meta:
        managed = True
        db_table = 'tblQmoneyPayment'
        app_label = 'qmoney_payment'