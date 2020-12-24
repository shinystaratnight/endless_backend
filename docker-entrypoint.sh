#!/bin/bash

rm -f celerybeat.pid

echo "Bower install starting..."
python manage.py bower_install --allow-root

echo "Collect static starting..."
python manage.py collectstatic --noinput

echo "Migrate starting..."
python manage.py migrate --noinput

echo "App starting..."
python manage.py runserver 0.0.0.0:8081
