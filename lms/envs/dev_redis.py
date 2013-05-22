"""
This config file follows the dev enviroment, but adds the
requirement of a celery worker running in the background to process
celery tasks.

The worker can be executed using:

django_admin.py celery worker
"""

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=W0401, W0614

from dev import *

################################# CELERY ######################################

# Requires a separate celery worker

CELERY_ALWAYS_EAGER = False

# Use django db as the broker and result store

CELERY_MESSAGE_COMPRESSION = None

BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Disable transaction management because we are using a worker. Views
# that request a task and wait for the result will deadlock otherwise.

#MIDDLEWARE_CLASSES = tuple(
#    c for c in MIDDLEWARE_CLASSES
#    if c != 'django.middleware.transaction.TransactionMiddleware')

# Note: other alternatives for disabling transactions don't work in 1.4
# https://code.djangoproject.com/ticket/2304
# https://code.djangoproject.com/ticket/16039
