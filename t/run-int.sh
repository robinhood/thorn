#!/bin/bash

python manage.py migrate --noinput
py.test -xsv t/integration --reuse-db
