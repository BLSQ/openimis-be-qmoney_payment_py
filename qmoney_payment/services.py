import datetime

from django.apps import apps
from django.db import transaction
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from qmoney_payment.apps import QMoneyPaymentConfig
from qmoney_payment.models.premium import get_premium_model, is_from_premium_app
from qmoney_payment.models.policy import get_policy_model


@transaction.atomic
def proceed(qmoney_payment, otp, user):
    if qmoney_payment.is_proceeded():
        # maybe "raise an info" to say it's already done
        return {'ok': True, 'status': qmoney_payment.status}
    if qmoney_payment.is_initiated():
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message':
            _('models.qmoney_payment.proceed.error.not_yet_requested')
        }
    if qmoney_payment.is_canceled():
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message': _('models.qmoney_payment.proceed.error.canceled')
        }

    # TODO manage the case the object has already been created, reuse ?
    merchant = apps.get_app_config(QMoneyPaymentConfig.name).merchant

    ok, reason = merchant.proceed(qmoney_payment.payment_transaction(), otp)
    if ok:
        qmoney_payment.set_status_after_proceed()
        create_premium_for(qmoney_payment, user)
    else:
        return {
            'ok':
            False,
            'status':
            qmoney_payment.status,
            'message':
            # Translators: This message will replace named-string reason
            _('models.qmoney_payment.proceed.error.failed').format(
                reason=reason)
            # Add more details
        }
    return {'ok': True, 'status': qmoney_payment.status}


def request(qmoney_payment):
    if qmoney_payment.is_waiting_for_confirmation():
        # Should probably not happen as the object is always created by the
        # mutation before requesting
        return {'ok': True, 'status': qmoney_payment.status}
    if qmoney_payment.is_proceeded():
        # Should probably not happen as the object is always created by the
        # mutation before requesting
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message':
            _('models.qmoney_payment.request.error.already_proceeded')
        }
    if qmoney_payment.is_canceled():
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message':
            _('models.qmoney_payment.request.error.already_canceled')
        }
    if qmoney_payment.is_policy_idle():
        return {
            'ok':
            False,
            'status':
            qmoney_payment.status,
            'message':
            # Translators: This message will replace named-string policy_uuid
            _('models.qmoney_payment.request.error.policy_not_idle').format(
                policy_uuid=qmoney_payment.policy_uuid)
        }

    # TODO manage the case the object has already been created, reuse ?
    config = apps.get_app_config(QMoneyPaymentConfig.name)

    transaction = config.merchant.request_payment(config.session,
                                                  qmoney_payment.payer_wallet,
                                                  qmoney_payment.amount)

    if not qmoney_payment.set_status_after_request(transaction):
        # TODO to manage, buuuuut except network error, it should be always ok due to the API :/
        # maybe with the get transaction state of their API ?
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message': _('models.qmoney_payment.request.error.failed')
        }
    return {'ok': True, 'status': qmoney_payment.status}


@transaction.atomic
def cancel(qmoney_payment):
    if qmoney_payment.payment_transaction().is_proceeded():
        # maybe "raise an info" to say it's already done
        return {
            'ok': False,
            'status': qmoney_payment.status,
            'message':
            _('models.qmoney_payment.cancel.error.already_proceeded')
        }

    qmoney_payment.set_status_after_cancel()
    return {'ok': True, 'status': qmoney_payment.status}


@transaction.atomic
def create_premium_for(qmoney_payment, user):
    if not qmoney_payment.is_proceeded():
        return (False, _('service.create_premium_for.error'))

    now = datetime.date.today()
    data = {
        'receipt': qmoney_payment.uuid,
        'amount': qmoney_payment.amount,
        'pay_type': 'M',
        'pay_date': now,
        'is_offline': False
    }

    if is_from_premium_app():
        update_or_create_premium = import_string(
            'contribution.gql_mutations.update_or_create_premium')

        data['policy_uuid'] = qmoney_payment.policy.uuid

        premium = update_or_create_premium(data, user)
    else:
        policy = qmoney_payment.policy
        data['policy'] = policy
        premium = get_premium_model().objects.create(**data)
        policy.status = get_policy_model().STATUS_ACTIVE
        policy.save()

    qmoney_payment.premium = premium
    qmoney_payment.save()
    return (True, premium)
