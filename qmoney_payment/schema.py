import uuid

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext as _

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError

from core import ExtendedConnection

from .apps import QMoneyPaymentConfig
from .models.qmoney_payment import QMoneyPayment
from .models.policy import get_policy_model
from .models.mutation_log import get_mutation_log_model


class QMoneyPaymentGQLType(DjangoObjectType):

    policy_uuid = graphene.UUID()
    uuid = graphene.UUID(source='uuid')
    premium_uuid = graphene.UUID()

    class Meta:
        model = QMoneyPayment
        interfaces = (graphene.relay.Node, )
        filter_fields = []
        connection_class = ExtendedConnection

    def resolve_policy_uuid(parent, info):
        if parent is None:
            return None
        return parent.policy_uuid

    def resolve_premium_uuid(parent, info):
        if parent is None:
            return None
        return parent.premium_uuid


def raise_if_not_authenticated(user):
    if type(user) is AnonymousUser or not user.id:
        raise ValidationError(_('mutation.authentication_required'))


def raise_if_is_not_authorized_to(user, gql_action):
    try:
        if not user.has_perms(
                apps.get_app_config(QMoneyPaymentConfig.name).
                get_gql_permission_for(gql_action)):
            raise PermissionDenied(_('unauthorized'))
    except AttributeError:
        raise PermissionDenied(_('unauthorized'))


class Query(graphene.ObjectType):
    qmoney_payment = graphene.Field(
        QMoneyPaymentGQLType,
        uuid=graphene.UUID(),
    )

    qmoney_payments = DjangoFilterConnectionField(
        QMoneyPaymentGQLType,
        policy_uuid=graphene.UUID(),
    )

    def resolve_qmoney_payment(root, info, uuid):
        user = info.context.user
        raise_if_not_authenticated(user)
        raise_if_is_not_authorized_to(user, 'get')

        try:
            return QMoneyPayment.objects.get(uuid=uuid)
        except QMoneyPayment.DoesNotExist:
            return None

    def resolve_qmoney_payments(root, info, policy_uuid=None):
        user = info.context.user
        raise_if_not_authenticated(user)
        raise_if_is_not_authorized_to(user, 'list')
        if policy_uuid is not None:
            return QMoneyPayment.objects.filter(policy__uuid=policy_uuid)
        return QMoneyPayment.objects.all()


class ProceedQMoneyPayment(graphene.Mutation):

    class Arguments:
        uuid = graphene.UUID()
        otp = graphene.String()

    ok = graphene.Boolean()
    qmoney_payment = graphene.Field(lambda: QMoneyPaymentGQLType)

    def mutate(root, info, uuid, otp):
        user = info.context.user
        raise_if_not_authenticated(user)
        raise_if_is_not_authorized_to(user, 'proceed')
        json_of_parameters = {'uuid': uuid, 'otp': otp}
        mutation_log = get_mutation_log_model().objects.create(
            json_content=json_of_parameters,
            user_id=user.id,
            client_mutation_label=f'Proceed QMoney Payment ({uuid}, otp: {otp})'
        )
        try:
            one_qmoney_payment = QMoneyPayment.objects.get(uuid=uuid)
        except QMoneyPayment.DoesNotExist:
            error_message = _('mutation.error.qmoney_payment.uuid_not_found')
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        response = one_qmoney_payment.proceed(otp, user)
        if not response['ok']:
            error_message = _(
                # Translators: This message will replace named-string status and reason
                'mutation.error.qmoney_payment.proceed_error').format(
                    status=response['status'], reason=response['message'])
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)
        ok = True
        mutation_log.mark_as_successful()
        return RequestQMoneyPayment(qmoney_payment=one_qmoney_payment, ok=ok)


class CancelQMoneyPayment(graphene.Mutation):

    class Arguments:
        uuid = graphene.UUID()

    ok = graphene.Boolean()
    qmoney_payment = graphene.Field(lambda: QMoneyPaymentGQLType)

    def mutate(root, info, uuid):
        user = info.context.user
        raise_if_not_authenticated(user)
        raise_if_is_not_authorized_to(user, 'proceed')
        json_of_parameters = {'uuid': uuid}
        mutation_log = get_mutation_log_model().objects.create(
            json_content=json_of_parameters,
            user_id=user.id,
            client_mutation_label=f'Cancel QMoney Payment ({uuid})')
        try:
            one_qmoney_payment = QMoneyPayment.objects.get(uuid=uuid)
        except QMoneyPayment.DoesNotExist:
            error_message = _('mutation.error.qmoney_payment.uuid_not_found')
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        response = one_qmoney_payment.cancel()
        if not response['ok']:
            error_message = _(
                # Translators: This message will replace named-string status and reason
                'mutation.error.qmoney_payment.cancel_error').format(
                    status=response['status'], reason=response['message'])
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        mutation_log.mark_as_successful()
        ok = True
        return CancelQMoneyPayment(qmoney_payment=one_qmoney_payment, ok=ok)


class RequestQMoneyPayment(graphene.Mutation):

    class Arguments:
        policy_uuid = graphene.UUID()
        amount = graphene.Int()
        payer_wallet = graphene.String()

    ok = graphene.Boolean()
    qmoney_payment = graphene.Field(lambda: QMoneyPaymentGQLType)

    def mutate(root, info, amount, payer_wallet, policy_uuid):
        user = info.context.user
        raise_if_not_authenticated(user)
        raise_if_is_not_authorized_to(user, 'request')

        json_of_parameters = {
            'amount': amount,
            'payer_wallet': payer_wallet,
            'policy_uuid': policy_uuid
        }
        mutation_log = get_mutation_log_model().objects.create(
            json_content=json_of_parameters,
            user_id=user.id,
            client_mutation_label=
            f'Request QMoney Payment (wallet: {payer_wallet}, amount: {amount}, policy: {policy_uuid})'
        )
        try:
            policy = get_policy_model().objects.get(uuid=policy_uuid)
        except get_policy_model().DoesNotExist:
            error_message = _('mutation.error.policy.uuid_not_found')
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        try:
            one_qmoney_payment = QMoneyPayment.objects.create(
                policy=policy, amount=amount, payer_wallet=payer_wallet)
            response = one_qmoney_payment.request()
        except ValidationError as error:
            error_message = error.message
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        if not response['ok']:
            error_message = _(
                # Translators: This message will replace named-string status and reason
                'mutation.error.qmoney_payment.request_error').format(
                    status=response['status'], reason=response['message'])
            mutation_log.mark_as_failed(error_message)
            return GraphQLError(error_message)

        mutation_log.mark_as_successful()
        ok = True
        return RequestQMoneyPayment(qmoney_payment=one_qmoney_payment, ok=ok)


class Mutation(graphene.ObjectType):
    request_qmoney_payment = RequestQMoneyPayment.Field()
    proceed_qmoney_payment = ProceedQMoneyPayment.Field()
    cancel_qmoney_payment = CancelQMoneyPayment.Field()
