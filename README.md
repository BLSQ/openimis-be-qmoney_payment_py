# OpenIMIS module: QMoney mobile payment

This OpenIMIS module, a standalone Django app, allows an enrollment officer to
add a new contribution (premium) paid by mobile phone via QMoney (a mobile
payment provider).

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

### Configuration

The module has to be configured through environment variables:

| name | description |
| - | - | 
| QMONEY_URL | The URL of the QMoney instance to use |
| QMONEY_USERNAME | Username of the QMoney account to use when requesting its API |
| QMONEY_PASSWORD | Password of the QMoney account to use when requesting its API |
QMONEY_TOKEN=Basic token to be authorized to call public endpoints such as login |
| QMONEY_PAYER | ID of the payer wallet |
| QMONEY_PAYEE | ID of the payee (or merchant) wallet |
| QMONEY_PAYEE_PIN_CODE | Pin code of the payee wallet |

For the permissions, it follows the OpenIMIS ways, here the ones you can use:

* `gql_qmoney_payment_get_permissions`
* `gql_qmoney_payment_list_permissions`
* `gql_qmoney_payment_request_permissions`
* `gql_qmoney_payment_proceed_permissions`

## Test

### Requirements

For test and developments, there are a few additional dependencies to install:

```bash
pip install -r requirements-dev.txt
```

TODO: tell how to do so when installed as an OpenIMIS module

### Settings

The tests are calling an actual staging instance of QMoney (we might update the
tests later to replace these calls with a mock). In addition to the QMoney URL,
you need to provide some settings such as the credentials or the wallet IDs of
the payer and payee.

This information has to be provided through the `.test.env` file. There is an
example that you can copy: `cp .test.env.example .test.env`. The file has to
be stored in the root directory of the present OpenIMIS module.

When the module is loaded in the whole OpenIMIS project, you need to put that
file into the root of the OpenIMIS project, aside the Python script
`manage.py`. Also you need to make sure the module has been added to the
`openimis.json` file.

TODO detail how to add it in openimis.json when you develop the module, or just
use it.

#### QMoney

As explained above, you need some information to run the tests. You'll get it
directly from QMoney. At the same time, make sure you provide a Gmail address.
This address will be linked to the payer wallet. That way, you'll receive a
QMoney One Time Password (OTP) when a payment is requested from that wallet.

#### Simple Gmail

In order to retrieve the OTP, the tests will programmatically access the Gmail
account that you have associated to the payer wallet (see previous section). To
do so we use the Python API client
[simplegmail](https://github.com/jeremyephron/simplegmail#getting-started).

This requires some setup on your side to work. First, you need to retrieve the
OAuth 2.0 Client ID file `client_secret.json` authorizing the tests. You'll
find it in 1Password (Bluesquare space - openIMIS vault). Notice that the Gmail
address that you'll use should belong to the Bluesquare domain. If you run it
on a CI, you'll need to that before in order to provide an additional file of
secret `gmail_token.json`.

### Run tests locally (as a standalone Django App)

Without the full Django test harness

```bash
pytest
```

As explained in the previous section, some tests rely on an existing GMail account. By default, those tests are skipped. You run also those tests with:

```bash
RUN_ALSO_TESTS_WITH_GMAIL=1 pytest
```

If you'd like to automate the run of your test when changes are saved, you can
use `pytest-watch`:

```bash
ptw
```

#### Collect coverage

```bash
pytest --cov=qmoney_payment --cov-report html
```

### Run tests with the full Django test harness

```bash
./manage.py test --keepdb qmoney_payment
```

If you want also run the tests using Gmail, you do as it follows:

```bash
RUN_ALSO_TESTS_WITH_GMAIL=1 ./manage.py test --keepdb qmoney_payment
```

## Linting

```bash
prospector
```

## Limitations

The QMoney has some inherent known limitations:

* When requesting a payment (and by doing so initiating the transaction), QMoney
  will respond that it succeeds as soon the payload is a well formated JSON and
  you have provided a valid access token. It means at that step we won't be able
  to know if the payer wallet is valid, if there is a chance that it contains
  enough money, if the pin code or the merchant wallet are the right ones, and
  so on.
* The message sent with the OTP to the payer doesn't contain any additional
  information. It seems there isn't any way to give them context.
* It seems there isn't any throttle or limit of transactions that you can
  initiate (so far it has been tested with 500 wrong OTP).
* It seems there isn't any expiration of the access token (so far it has been
  tested with a 80 days old access token).
* There isn't any information regarding the expiration in the access token, that
  is a JWT token.

Pending questions:

* limit on the number of attemps to verify a payment (after 500 failed attempts,
  it's still possible to confirm the payment with a correct OTP)
* limit on OTP validity
* expiration of access token (it seems there isn't as we receive `-1`)
* what's in the access token, that is a JWT token
* details about `getTransactionStatus`
