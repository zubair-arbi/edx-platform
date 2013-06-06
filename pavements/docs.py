# --- Develop and public documentation ---
import os
from paver.easy import task, needs, consume_args, no_help
from subprocess import call

from pavements.config import config
from pavements.helpers import *

import webbrowser


@task
@consume_args
def builddocs(args):
    """ Invoke sphinx 'make build' to generate docs. """
    if 'pub' in args:
        path = "doc/public"
    else:
        path = "docs"

    with cd(os.path.join(config['REPO_ROOT'], path)):
        call(['make', 'html'])


@task
@consume_args
def showdocs(args):
    """
    Show docs in browser.
    """
    if "pub" in args:
        path = "doc/public"
    else:
        path = "docs"
    
    url = "file://" + os.path.join(config["REPO_ROOT"], path, "build/html/index.html")
    webbrowser.open(url)


@task
@needs(['builddocs', 'showdocs'])
@consume_args
def doc(args):
    """Build docs and show them in browser"""
