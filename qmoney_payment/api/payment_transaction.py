from enum import Enum

from django.utils.translation import gettext as _


class PaymentTransaction:
    to_merchant = None
    from_wallet_id = None
    amount_to_pay = 0
    session = None
    transaction_id = None
    State = Enum('State', [
        'INITIATED', 'WAITING_FOR_CONFIRMATION', 'PROCEEDED', 'UNKNOWN',
        'FAILED', 'CANCELED'
    ])
    current_state = State.UNKNOWN

    def __init__(  # pylint: disable=too-many-arguments
            self,
            with_session,
            to_merchant,
            from_wallet_id,
            amount,
            state_initial='I',
            assigned_transaction_id=None):
        self.to_merchant = to_merchant
        self.from_wallet_id = from_wallet_id
        self.amount_to_pay = amount
        self.session = with_session
        self.transaction_id = assigned_transaction_id
        self.current_state = self.__convert_state_initial_to_state_enum(
            state_initial)

    def __convert_state_initial_to_state_enum(self, state_initial):
        return next(
            iter([
                elem for elem in PaymentTransaction.State
                if state_initial in (elem.name[0], elem.name)
            ]), PaymentTransaction.State.UNKNOWN)

    def is_initiated(self):
        return self.current_state == PaymentTransaction.State.INITIATED

    def is_waiting_for_confirmation(self):
        return self.current_state == PaymentTransaction.State.WAITING_FOR_CONFIRMATION

    def is_proceeded(self):
        return self.current_state == PaymentTransaction.State.PROCEEDED

    def is_failed(self):
        return self.current_state == PaymentTransaction.State.FAILED

    def is_in_unknown_state(self):
        return self.current_state == PaymentTransaction.State.UNKNOWN

    def is_canceled(self):
        return self.current_state == PaymentTransaction.State.CANCELED

    def state(self):
        return self.current_state

    def amount(self):
        return self.amount_to_pay

    def payer(self):
        return self.from_wallet_id

    def merchant(self):
        return self.to_merchant

    def request_otp(self):
        transaction_id = self.session.get_money(self.from_wallet_id,
                                                self.to_merchant.wallet_id,
                                                self.amount_to_pay,
                                                self.to_merchant.pin_code)

        if transaction_id is not None:
            self.current_state = PaymentTransaction.State.WAITING_FOR_CONFIRMATION
            self.transaction_id = transaction_id
        else:
            self.current_state = PaymentTransaction.State.FAILED

        return transaction_id is not None

    def proceed(self, otp):
        if self.transaction_id is None:
            return False, _('qmoney_payment.proceed.error.transaction_empty')
        if otp is None:
            return False, _('qmoney_payment.proceed.error.otp_empty')
        result = self.session.verify_code(self.transaction_id, otp)
        if result[0]:
            self.current_state = PaymentTransaction.State.PROCEEDED
        else:
            self.current_state = PaymentTransaction.State.FAILED
        return result