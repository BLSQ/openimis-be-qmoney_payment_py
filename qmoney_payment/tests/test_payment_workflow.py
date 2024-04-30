import os
import time
import unittest
from unittest import TestCase

from simplegmail import Gmail

from qmoney_payment.api.payment_transaction import PaymentTransaction
from qmoney_payment.api.client import Client as QMoneyClient
from .helpers import gmail_wait_and_get_recent_emails_with_qmoney_otp, current_datetime, extract_otp_from_email_messages, gmail_mark_messages_as_read, gmail_mark_as_read_recent_emails_with_qmoney_otp
from .qmoney_helpers import qmoney_url, qmoney_token, qmoney_credentials, qmoney_access_token, qmoney_getmoney_json_payload, qmoney_payee, qmoney_payer, qmoney_payee_pin_code


@unittest.skipIf('RUN_ALSO_TESTS_WITH_GMAIL' not in os.environ,
                 'Skipping tests using Gmail')
class TestPaymentWorkflow(TestCase):

    @classmethod
    def gmail_client(cls):
        client = Gmail()
        time.sleep(5)
        gmail_mark_as_read_recent_emails_with_qmoney_otp(client)
        return client

    @classmethod
    def setUpClass(cls):
        cls._qmoney_url = qmoney_url()
        cls._qmoney_credentials = qmoney_credentials()
        cls._qmoney_token = qmoney_token()
        cls._qmoney_payee = qmoney_payee()
        cls._qmoney_payer = qmoney_payer()
        cls._qmoney_payee_pin_code = qmoney_payee_pin_code()
        cls._gmail_client = cls.gmail_client()

    @classmethod
    def tearDownClass(cls):
        gmail_mark_as_read_recent_emails_with_qmoney_otp(cls._gmail_client)

    def test_succeeding_whole_payment_workflow_with_right_inputs(self):
        amount = 1
        before_initiating_transaction = current_datetime()
        session = QMoneyClient.session(
            TestPaymentWorkflow._qmoney_url,
            TestPaymentWorkflow._qmoney_credentials[0],
            TestPaymentWorkflow._qmoney_credentials[1],
            TestPaymentWorkflow._qmoney_token)
        merchant = session.merchant(TestPaymentWorkflow._qmoney_payee,
                                    TestPaymentWorkflow._qmoney_payee_pin_code)
        payment_transaction = merchant.request_payment(
            session, TestPaymentWorkflow._qmoney_payer, amount)

        assert payment_transaction.state(
        ) == PaymentTransaction.State.WAITING_FOR_CONFIRMATION

        messages = gmail_wait_and_get_recent_emails_with_qmoney_otp(
            TestPaymentWorkflow._gmail_client, 10, 300)

        otp = extract_otp_from_email_messages(messages,
                                              before_initiating_transaction)

        gmail_mark_messages_as_read(messages)

        (result, response) = payment_transaction.proceed(otp)
        assert result is True, f'Something went wrong, here the response: {response}'
        assert payment_transaction.state(
        ) == PaymentTransaction.State.PROCEEDED
        assert payment_transaction.amount() == amount
        assert payment_transaction.payer() == TestPaymentWorkflow._qmoney_payer
        assert payment_transaction.merchant() == merchant