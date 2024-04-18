#!/bin/env bash

django-admin makemessages -l en -e py -i . -v3 --pythonpath "$(pwd)" --settings=qmoney_payment.test_settings
django-admin compilemessages -v3 --pythonpath "$(pwd)" --settings=qmoney_payment.test_settings
