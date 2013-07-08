import os
import sys
import platform
import resource
import glob2
from paver.easy import task, needs, cmdopts, no_help
from subprocess import call, Popen
from optparse import make_option

from pavements.config import config
from pavements.helpers import *

THEME_NAME = os.environ.get('THEME_NAME', False)
USE_CUSTOM_THEME = THEME_NAME and not is_empty(THEME_NAME)
if USE_CUSTOM_THEME:
    THEME_ROOT = os.path.join(config['REPO_ROOT'], "themes", THEME_NAME)
    THEME_SASS = os.path.join(THEME_ROOT, "static", "sass")


def xmodule_cmd(watch=False, debug=False):
    """ Generate the shell command needed to run xmodule for these given arguments """
    xmodule_cmd_string = 'xmodule_assets common/static/xmodule'
    if watch:
        return ("watchmedo shell-command " +
                "--patterns='*.js;*.coffee;*.sass;*.scss;*.css' " +
                "--recursive " +
                "--command='%s' " +
                "common/lib/xmodule") % xmodule_cmd_string
    else:
        return xmodule_cmd_string

MINIMAL_DARWIN_NOFILE_LIMIT = 8000

def coffee_cmd(watch=False, debug=False):
    """ Generate the shell command needed to run sass for these given arguments """
    if watch and platform.system() == 'Darwin':
        available_files = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        if available_files < MINIMAL_DARWIN_NOFILE_LIMIT:
            resource.setrlimit(resource.RLIMIT_NOFILE, MINIMAL_DARWIN_NOFILE_LIMIT)
    return 'node_modules/.bin/coffee --compile %s .' % ('--watch' if watch else '')


def sass_cmd(watch=False, debug=False):
    """ Generate the shell command needed to run sass for these given arguments """
    sass_load_paths = ["./common/static/sass"]
    sass_watch_paths = ["*/static"]
    if USE_CUSTOM_THEME:
        sass_load_paths.append(THEME_SASS)
        sass_watch_paths.append(THEME_SASS)

    return ("sass %s " % ('--debug-info' if debug else '--style compressed') +
            "--load-path %s " % (' '.join(sass_load_paths)) +
            "--require ./common/static/sass/bourbon/lib/bourbon.rb " +
            "%s %s") % ('--watch' if watch else '--update', ' '.join(sass_watch_paths))


@task
def preprocess():
    """Preprocess all templatized static asset files"""
    system = 'lms'
    env = 'dev'

    status = os.system(django_admin(system, env, "preprocess_assets"))
    if status > 0:
        print "asset preprocessing failed!"
        sys.exit()


#############################
#
# Bare assets tasks
#
##############################


@task
@needs("pavements.prereqs.install_python_prereqs")
def assets_xmodule():
    """Compile all xmodule assets"""
    call(xmodule_cmd(watch=False, debug=False), shell=True)


@task
@needs("pavements.prereqs.install_node_prereqs")
def assets_coffee():
    """Compile all coffeescript assets"""
    call(coffee_cmd(watch=False, debug=False), shell=True)


@task
@needs("pavements.prereqs.install_ruby_prereqs", "preprocess")
def assets_sass():
    """Compile all sass assets"""
    call(sass_cmd(watch=False, debug=False), shell=True)


@task
@needs("assets_coffee", "assets_sass", "assets_xmodule")
def assets_all():
    """ Compile all assets """
    pass

################################
#
# Assets debug tasks
#
#################################


@task
@needs("pavements.prereqs.install_python_prereqs")
def assets_xmodule_debug():
    """Compile all xmodule assets in debug mode"""
    call(xmodule_cmd(watch=False, debug=True), shell=True)


@task
@needs("pavements.prereqs.install_node_prereqs", "assets_coffee_clobber")
def assets_coffee_debug():
    """Compile all coffee assets in debug mode"""
    call(coffee_cmd(watch=False, debug=True), shell=True)


@task
@needs("pavements.prereqs.install_ruby_prereqs", "preprocess")
def assets_sass_debug():
    """Compile all sass assets in debug mode"""
    call(sass_cmd(watch=False, debug=True), shell=True)

#################################
#
# Assets watch tasks
#
#################################


@task
@needs("assets_xmodule_debug")
def assets_xmodule_watch():
    """Compile all xmodule assets with a watcher"""
    Popen(xmodule_cmd(watch=True, debug=True), shell=True)


@task
@needs("assets_coffee_debug")
def assets_coffee_watch():
    """Compile all coffeescript assets with a watcher"""
    Popen(coffee_cmd(watch=True, debug=True), shell=True)


@task
@needs("assets_sass_debug")
def assets_sass_watch():
    """Compile all sass assets with a watcher"""
    Popen(sass_cmd(watch=True, debug=True), shell=True)


@task
@needs('assets_sass_watch', 'assets_coffee_watch', 'assets_xmodule_watch')
def assets_watch_all():
    """ Compile and watch all assets """
    pass


@task
def assets_coffee_clobber():
    """ Deletes all compiled coffeescript files"""
    path = '*/static/coffee/**/*.js'
    for file_path in glob2.glob(path):
        print 'deleting file {0}'.format(file_path)
        os.remove(file_path)

##################################
#
# Gather Assets
#
##################################


@task
@needs('pavements.assets.assets_all')
@cmdopts([
    make_option('-s', '--system', dest='system', default='lms', help='The system (lms, cms) we would like to gather assets for'),
    make_option('-e', '--env', dest='env', default='dev', help='The environment (dev, test,...) that we would like to gather the assets for')
])
def gather_assets(options):
    """ Gather all assets for the given system and environment """
    print 'Gathering assets for system {0} and enviornment {1}'.format(options.system, options.env)
    status = os.system(django_admin(options.system, options.env, 'collectstatic', '--noinput'))
    if status > 0:
        print "collectstatic failed!"
        sys.exit()
