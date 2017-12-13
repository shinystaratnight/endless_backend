#!/bin/bash

rm -f celerybeat.pid

echo "Bower install starting..."
bin/django bower_install --allow-root

echo "Collect static starting..."
bin/django collectstatic --noinput

echo "Migrate starting..."
bin/django migrate --noinput

echo "App starting..."
bin/app start
