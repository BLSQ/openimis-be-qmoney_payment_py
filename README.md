# OpenIMIS module: QMoney mobile payment

This mobile allows an enrollment officer to add a new contribution paid by mobile phone
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

The tests are calling an actual staging instance of QMoney (we might update the tests later to 
replace these calls with a mock). In addition to the QMoney URL, you need to provide some
settings such as the credentials or the wallet IDs of the payer and payee.

This information has to be provided through the `.test.env` file. There is
an example that you can copy: `cp .test.env.example .test.env`.

#### QMoney

As explained above, you need some information to run the tests. You'll get
it directly from QMoney. At the same time, make sure you provide a Gmail
address. This address will be linked to the payer wallet. That way, you'll receive
a QMoney One Time Password (OTP) when a payment is requested from that wallet.

#### Simple Gmail

In order to retrieve the OTP, the tests will programmatically access the Gmail
account that you have associated to the payer wallet (see previous section). To
do so we use the Python API client
[simplegmail](https://github.com/jeremyephron/simplegmail#getting-started).

This requires some setup on your side to work. First, you need to retrieve the
OAuth 2.0 Client ID file `client_secret.json` authorizing the tests. You'll
find it in 1Password (Bluesquare space - openIMIS vault). Notice that the Gmail address that
you'll use should belong to the Bluesquare domain. If you run it on a CI,
you'll need to that before in order to provide an additional file of secret
`gmail_token.json`.

### Run tests locally

Without the full OpenIMIS test harness

```bash
pytest
```