from qmoney_payment.api.payment_transaction import PaymentTransaction


class Merchant:
    wallet_id = None
    pin_code = None

    def __init__(self, wallet_id, pin_code):
        self.wallet_id = wallet_id
        self.pin_code = pin_code

    def request_payment(self, session, from_wallet_id, amount):
        payment_transaction = PaymentTransaction(session, self, from_wallet_id,
                                                 amount)
        payment_transaction.request_otp()
        return payment_transaction

    def proceed(self, payment_transaction, otp):
        return payment_transaction.proceed(otp)