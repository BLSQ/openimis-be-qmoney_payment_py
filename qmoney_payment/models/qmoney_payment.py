import uuid

from django.apps import apps
from django.core.validators import MinValueValidator, ValidationError
from django.db import models
from django.db.models import Count, Q
from django.db import transaction as django_db_transaction
from django.utils.translation import gettext as _

from qmoney_payment.apps import QMoneyPaymentConfig
from qmoney_payment.qmoney import PaymentTransaction
from qmoney_payment.models.policy import get_policy_model
from qmoney_payment.models.premium import get_premium_model
from qmoney_payment.services import create_premium_for


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
                'ok':
                False,
                'status':
                self.status,
                'message':
                _('models.qmoney_payment.request.error.already_proceeded')
            }
        if self.payment_transaction().is_canceled():
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                _('models.qmoney_payment.request.error.already_canceled')
            }
        if self.policy.status is not get_policy_model().STATUS_IDLE:
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                # Translators: This message will replace named-string policy_uuid
                _('models.qmoney_payment.request.error.policy_not_idle'
                  ).format(policy_uuid=self.policy_uuid)
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
                'message': _('models.qmoney_payment.request.error.failed')
            }
        return {'ok': True, 'status': self.status}

    @django_db_transaction.atomic
    def cancel(self):
        if self.payment_transaction().is_proceeded():
            # maybe "raise an info" to say it's already done
            return {
                'ok':
                False,
                'status':
                self.status,
                'message':
                _('models.qmoney_payment.cancel.error.already_proceeded')
            }

        self.status = QMoneyPayment.Status.C
        self.save()
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
                _('models.qmoney_payment.proceed.error.not_yet_requested')
            }
        if self.payment_transaction().is_canceled():
            return {
                'ok': False,
                'status': self.status,
                'message': _('models.qmoney_payment.proceed.error.canceled')
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
                # Translators: This message will replace named-string reason
                _('models.qmoney_payment.proceed.error.failed').format(
                    reason=response[1])
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

    def save(self, *args, **kwargs):
        if self.policy is not None:
            policy_from_db = get_policy_model(
            ).objects.filter(id=self.policy.id).annotate(
                ongoing_unproceeded_transactions=Count(
                    'qmoneypayment__policy__pk',
                    filter=~Q(qmoneypayment__status__exact=self.Status.P)
                    | ~Q(qmoneypayment__status__exact=self.Status.C))).first()
            if policy_from_db is not None and policy_from_db.ongoing_unproceeded_transactions > self.MAX_SIMULTANEOUS_UNPROCEEDED_TRANSACTIONS:
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
