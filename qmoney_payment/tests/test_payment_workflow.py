import pytest

from qmoney_payment.qmoney import QMoney, PaymentTransaction
from helpers import gmail_wait_and_get_recent_emails_with_qmoney_otp, current_datetime, extract_otp_from_email_messages, gmail_mark_messages_as_read


@pytest.mark.with_gmail
class TestPaymentWorkflow:

    def test_happy_path(self, qmoney_url, qmoney_credentials, qmoney_token,
                        qmoney_payer, qmoney_payee, qmoney_payee_pin_code,
                        gmail_client):
        amount = 1
        before_initiating_transaction = current_datetime()
        session = QMoney.session(qmoney_url, qmoney_credentials[0],
                                 qmoney_credentials[1], qmoney_token)
        merchant = session.merchant(qmoney_payee, qmoney_payee_pin_code)
        payment_transaction = merchant.request_payment(session, qmoney_payer,
                                                       amount)

        assert payment_transaction.state(
        ) == PaymentTransaction.State.WAIT_FOR_CONFIRMATION

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        result = payment_transaction.proceed(otp)
        assert result is True
        assert payment_transaction.state(
        ) == PaymentTransaction.State.PROCEEDED
        assert payment_transaction.amount() == amount
        assert payment_transaction.payer() == qmoney_payer
        assert payment_transaction.merchant() == merchant
