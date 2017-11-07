#!/bin/bash

if [ "$DJANGO_DEBUG" == "1" ]; then
    bin/pip install -r dependencies/pip_pytest.txt
else
    bin/pip install -r dependencies/pip_py3.txt
fi;

bin/django migrate --noinput
bin/django bower_install -R

if [ "$DJANGO_DEBUG" == "0" ]; then
    bin/django collectstatic --noinput
    touch var/run/uwsgi_reload
    echo Starting uwsgi daemod.
    exec bin/uwsgi conf/production/uwsgi.ini
else
    exec bin/django runserver 0.0.0.0:$DJANGO_UWSGI_PORT
fi;
