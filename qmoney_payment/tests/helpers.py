import requests


class QMoneyBasicAuth(requests.auth.AuthBase):

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f'Basic {self.token}'
        return r


class QMoneyBearerAuth(requests.auth.AuthBase):

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f'Bearer {self.token}'
        return r


class QMoney:

    @classmethod
    def login(cls, url, credentials, token, raw=False):
        json_payload = {
            'grantType': 'password',
            'username': credentials[0],
            'password': credentials[1],
        }
        response = requests.post(url=f'{url}/login',
                                 json=json_payload,
                                 auth=QMoneyBasicAuth(token))
        if raw:
            return response
        return response.json()['data']['access_token']


def get_from(the_map, keys):
    if the_map is None or len(the_map) == 0:
        return None
    if keys is None or len(keys) == 0:
        return None
    if len(keys) == 1:
        return the_map.get(keys[0], None)
    return get_from(the_map[keys[0]], keys[1:])


def del_from(the_map, keys):
    if the_map is None or len(the_map) == 0:
        return None
    if keys is None or len(keys) == 0:
        return None
    if len(keys) == 1:
        del the_map[keys[0]]
    else:
        del_from(the_map[keys[0]], keys[1:])
    return the_map


def set_into(the_map, keys, value):
    if the_map is None:
        return None
    if keys is None or len(keys) == 0:
        return None
    if len(keys) == 1:
        the_map[keys[0]] = value
    else:
        set_into(the_map[keys[0]], keys[1:], value)
    return the_map