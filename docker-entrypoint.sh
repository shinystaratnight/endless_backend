#!/bin/bash

rm -f celerybeat.pid

echo "Bower install starting..."
django bower_install --allow-root

echo "Collect static starting..."
django collectstatic --noinput

echo "Migrate starting..."
django migrate --noinput

echo "App starting..."
app start
