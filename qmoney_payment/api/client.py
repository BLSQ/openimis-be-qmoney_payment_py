from qmoney_payment.api.session import Session


class Client:

    @classmethod
    def session(cls, url, username, password, login_token):
        return Session(url, username, password, login_token)