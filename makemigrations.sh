#!/bin/env bash

django-admin makemigrations -v3 --pythonpath "$(pwd)" --settings=qmoney_payment.test_settings
