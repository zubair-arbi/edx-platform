import os
from paver.easy import task, needs, consume_args, no_help
from subprocess import call

from pavements.config import config
from pavements.helpers import *
from pavements.prereqs import install_python_prereqs


DEFAULT_OPTIONS = {
    'lms': '8000',
    'cms': '8001',
}


@task
@needs('pavements.prereqs.install_python_prereqs')
def predjango():
    """ Clean up the pyc files and install local requirements"""
    os.system("find . -type f -name *.pyc -delete", shell=True)
    os.system('pip install -q --no-index -r requirements/edx/local.txt')
