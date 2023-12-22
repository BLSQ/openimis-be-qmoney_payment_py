# OpenIMIS module: QMoney mobile payment

TODO Description

## Usage

TODO

## Test

### locally

Without the full OpenIMIS test harness

```bash
pytest
```

## Development

TODO

Qmoney:
- request env vars (see `.test.env`)
- request to associate a given email address to the provided merchant account

Gmail credentials (for test purpose):
https://github.com/jeremyephron/simplegmail#getting-started

As a resul, you'll get a `client_secret.json` file to put at the root of the
project.

The first time you'll run the test, you'll be asked in the browser to accept
with a Gmail account. You should be a member of the blsq org. If you run it on
a CI, you'll need to that before in order to provide an additional file of
secret `gmail_token.json`.