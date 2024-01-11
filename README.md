# OpenIMIS module: QMoney mobile payment

This mobile allows an admin to add a new contribution paid by mobile phone
via QMoney (a mobile payment provider).

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

TODO

## Test

### Requirements

For test and developments, there are a few additional dependencies to install:

```bash
pip install -r requirements-dev.txt
```

### Settings

The tests are run agains an actual staging instance of QMoney (later we might
add test working with mock). In addition to its URL, you need to provide some
settings such as the credentials or the wallet IDs of the payer and payee.

Those information have to be provided through the `.test.env` file. There is
an example that you can copy: `cp .test.env.example .test.env`.

#### QMoney

As explained above, you need several information to run the test. You'll get
those directly from QMoney. At the same time, make sure you provide a GMail
address. This address will be linked to the payer wallet. That way, you'll get
QMoney One Time Password (OTP) when a payment is requested from that wallet.

#### Simple GMail

In order to retrieve the OTP, the tests will programmatically access the GMail
account that you have associated to the payer wallet (see previous section). To
do so we use the Python API client
[simplegmail](https://github.com/jeremyephron/simplegmail#getting-started).

This requires some setup on your side to work. First, you need to retrieve the
OAuth 2.0 Client ID file `client_secret.json` authorizing the tests. You'll
find it in 1Password (Bluesquare space). Notice that the GMail address that
you'll use should belong to the Bluesquare domain. If you run it on a CI,
you'll need to that before in order to provide an additional file of secret
`gmail_token.json`.

### locally

Without the full OpenIMIS test harness

```bash
pytest
```