#!/bin/bash

python manage.py migrate --no-input
py.test -xsv t/integration --reuse-db
