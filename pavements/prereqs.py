import os
from paver.easy import task, needs, consume_args, no_help

from pavements.config import config
from pavements.helpers import *
import distutils.sysconfig as dusc


@task
@needs('pavements.prereqs.install_node_prereqs',
       'pavements.prereqs.install_ruby_prereqs',
       'pavements.prereqs.install_python_prereqs')
def install_prereqs():
    """Install preprequisiites needed for the lms and cms"""
    pass


@task
@needs('pavements.ws.migrate')
def install_node_prereqs():
    """Install all ruby prerequisites for the lms and cms"""
    unchanged = 'Node requirements unchanged, nothing to install'
    if when_changed(unchanged, ['package.json']) and not os.environ.get('NO_PREREQ_INSTALL'):
        os.system('npm install')


@task
@needs('pavements.ws.migrate')
def install_ruby_prereqs():
    """Install all python prerequisites for the lms and cms"""
    unchanged = 'Ruby requirements unchanged, nothing to install'
    if when_changed(unchanged, ['Gemfile']) and not os.environ.get('NO_PREREQ_INSTALL'):
        os.system('bundle install')

@task
@needs('pavements.ws.migrate')
def install_python_prereqs():
    """Install all python prerequisites for the lms and cms"""
    site_packages_dir = dusc.get_python_lib()
    unchanged = 'Python requirements unchanged, nothing to install'
    if (when_changed(unchanged, ['requirements/**/*'], [site_packages_dir]) and
        not os.environ.get('NO_PREREQ_INSTALL'):
        ENV['PIP_DOWNLOAD_CACHE'] ||= '.pip_download_cache'
        sh('pip install --exists-action w -r requirements/edx/pre.txt')
        sh('pip install --exists-action w -r requirements/edx/base.txt')
        sh('pip install --exists-action w -r requirements/edx/post.txt')
        # requirements/private.txt is used to install our libs as
        # working dirs, or for personal-use tools.
        if File.file?("requirements/private.txt")
            sh('pip install -r requirements/private.txt')
        end
    end unless ENV['NO_PREREQ_INSTALL']
