#!/usr/bin/env python
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def set_env():
    configs = ['env_defaults', '.env']
    for config in configs:
        if os.path.isfile(os.path.join(BASE_DIR, config)):
            with open(os.path.join(BASE_DIR, config), 'r') as f:
                for line in f.readlines():
                    if not line.strip():
                        continue
                    var, value = line.split('=', 1)
                    os.environ[var.strip()] = value.strip().strip('"')


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "r3sourcer.settings.prod")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    set_env()
    execute_from_command_line(sys.argv)
