import uuid

from django.apps import apps
from django.core.validators import MinValueValidator
from django.db import models

from qmoney_payment.apps import QMoneyPaymentConfig
from qmoney_payment.qmoney import PaymentTransaction
from qmoney_payment.models.policy import Policy


class QMoneyPayment(models.Model):

    class Status(models.TextChoices):
        INITIATED = 'I', 'Initiated'
        WAITING_FOR_CONFIRMATION = 'W', 'Waiting For Confirmation'
        PROCEEDED = 'P', 'Proceeded'

    uuid = models.UUIDField(primary_key=True,
                            default=uuid.uuid4,
                            editable=False)
    policy = models.ForeignKey('Policy',
                               on_delete=models.CASCADE,
                               to_field='uuid',
                               blank=True,
                               null=True)
    contribution_uuid = models.UUIDField(null=True, blank=True)
    external_transaction_id = models.CharField(max_length=200,
                                               null=True,
                                               blank=True)
    status = models.CharField(choices=Status.choices,
                              default=Status.INITIATED,
                              max_length=1)
    transaction = None

    # TODO Decide the precision: unity, dime, centime
    amount = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    payer_wallet = models.CharField(max_length=200)

    def request(self):
        if self.status == QMoneyPayment.Status.WAITING_FOR_CONFIRMATION:
            # Should probably not happen as the object is always created by the
            # mutation before requesting
            return {'ok': True, 'status': self.status}
        if self.status == QMoneyPayment.Status.PROCEEDED:
            # Should probably not happen as the object is always created by the
            # mutation before requesting
            return {
                'ok': False,
                'status': self.status,
                'message': 'The payment has already been proceeded.'
            }
        if self.policy.status is not Policy.STATUS_IDLE:
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                f'The Policy {self.policy.uuid} should be Idle but it is not.'
            }

        # TODO manage the case the object has already been created, reuse ?
        self.transaction = self.merchant().request_payment(
            self.session(), self.payer_wallet, self.amount)
        if self.transaction.current_state == PaymentTransaction.State.WAITING_FOR_CONFIRMATION:
            self.status = QMoneyPayment.Status.WAITING_FOR_CONFIRMATION
            self.external_transaction_id = self.transaction.transaction_id
            self.save()
        else:
            # TODO to manage, buuuuut except network error, it should be always ok due to the API :/
            # maybe with the get transaction state of their API ?
            return {
                'ok': False,
                'status': self.status,
                'message': 'The request could not have been made.',
                # Add more details
            }
        return {'ok': True, 'status': self.status}

    def proceed(self, otp):
        if self.status == QMoneyPayment.Status.PROCEEDED:
            # maybe "raise an info" to say it's already done
            return {'ok': True, 'status': self.status}
        if self.status == QMoneyPayment.Status.INITIATED:
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                'The payment has been requested. Please request it first before proceeding it.'
            }

        # TODO manage the case the object has already been created, reuse ?
        response = self.payment_transaction().proceed(otp)
        if response[0]:
            self.status = QMoneyPayment.Status.PROCEEDED
            self.save()
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
        config = apps.get_app_config("qmoney_payment")
        return config.merchant

    def session(self):
        config = apps.get_app_config("qmoney_payment")
        return config.session

    def payment_transaction(self):
        if self.transaction is not None:
            return self.transaction
        self.transaction = PaymentTransaction(self.session(), self.merchant(),
                                              self.payer_wallet, self.amount)
        self.transaction.transaction_id = self.external_transaction_id
        return self.transaction

    class Meta:
        managed = True