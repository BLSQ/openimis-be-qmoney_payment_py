import graphene

from core import ExtendedConnection

import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError

from .models.qmoney_payment import QMoneyPayment
from .models.policy import get_policy_model


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


class Query(graphene.ObjectType):
    #TODO autz
    qmoney_payment = graphene.Field(
        QMoneyPaymentGQLType,
        uuid=graphene.UUID(),
    )

    qmoney_payments = DjangoFilterConnectionField(
        QMoneyPaymentGQLType,
        policy_uuid=graphene.UUID(),
    )

    def resolve_qmoney_payment(root, info, uuid):
        # authz
        try:
            return QMoneyPayment.objects.get(uuid=uuid)
        except QMoneyPayment.DoesNotExist:
            return None

    def resolve_qmoney_payments(root, info, policy_uuid=None):
        # authz
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
        # authz
        try:
            one_qmoney_payment = QMoneyPayment.objects.get(uuid=uuid)
        except QMoneyPayment.DoesNotExist:
            return GraphQLError(
                'The UUID does not correspond to any recorded QMoney payment.')

        response = one_qmoney_payment.proceed(otp)
        if not response['ok']:
            return GraphQLError(
                f'Something went wrong. The payment could not be proceeded. The transaction is {response["status"]}. Reason: {response["message"]}'
            )
        ok = True
        return RequestQMoneyPayment(qmoney_payment=one_qmoney_payment, ok=ok)


class RequestQMoneyPayment(graphene.Mutation):

    class Arguments:
        policy_uuid = graphene.UUID()
        amount = graphene.Int()
        payer_wallet = graphene.String()

    ok = graphene.Boolean()
    qmoney_payment = graphene.Field(lambda: QMoneyPaymentGQLType)

    def mutate(root, info, amount, payer_wallet, policy_uuid):
        # authz
        try:
            # What if a transaction is ongoing?
            policy = get_policy_model().objects.get(uuid=policy_uuid)
        except get_policy_model().DoesNotExist:
            return GraphQLError(
                'The UUID does not correspond to any existing policy.')

        one_qmoney_payment = QMoneyPayment.objects.create(
            policy=policy, amount=amount, payer_wallet=payer_wallet)
        response = one_qmoney_payment.request()
        if not response['ok']:
            return GraphQLError(
                f'Something went wrong. The payment could not be requested. The transaction is {response["status"]}. Reason: {response["message"]}'
            )
        ok = True
        return RequestQMoneyPayment(qmoney_payment=one_qmoney_payment, ok=ok)


class Mutation(graphene.ObjectType):
    request_qmoney_payment = RequestQMoneyPayment.Field()
    proceed_qmoney_payment = ProceedQMoneyPayment.Field()
