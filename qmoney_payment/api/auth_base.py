from requests.auth import AuthBase


class QMoneyBasicAuth(AuthBase):

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f'Basic {self.token}'
        return r


class QMoneyBearerAuth(AuthBase):

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f'Bearer {self.token}'
        return r
