import datetime

from django.db import transaction
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from qmoney_payment.models.premium import get_premium_model
from qmoney_payment.models.premium import is_from_premium_app
from qmoney_payment.models.policy import get_policy_model


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
