#!/usr/bin/env python

"""
See https://edx-wiki.atlassian.net/wiki/display/ENG/PO+File+workflow

This task extracts all English strings from all source code
and produces three human-readable files:
   conf/locale/en/LC_MESSAGES/django-partial.po
   conf/locale/en/LC_MESSAGES/djangojs.po
   conf/locale/en/LC_MESSAGES/mako.po

This task will clobber any existing django.po file.
This is because django-admin.py makemessages hardcodes this filename
and it cannot be overridden.

"""

import os, sys, logging
from datetime import datetime
from polib import pofile

from i18n.config import BASE_DIR, LOCALE_DIR, CONFIGURATION
from i18n.execute import execute, create_dir_if_necessary, remove_file
from i18n.segment import segment_pofiles


# BABEL_CONFIG contains declarations for Babel to extract strings from mako template files
# Use relpath to reduce noise in logs
BABEL_CONFIG = BASE_DIR.relpathto(LOCALE_DIR.joinpath('babel.cfg'))

# Strings from mako template files are written to BABEL_OUT
# Use relpath to reduce noise in logs
BABEL_OUT = BASE_DIR.relpathto(CONFIGURATION.source_messages_dir.joinpath('mako.po'))

SOURCE_WARN = 'This English source file is machine-generated. Do not check it into git.'

LOG = logging.getLogger(__name__)

def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    create_dir_if_necessary(LOCALE_DIR)
    source_msgs_dir = CONFIGURATION.source_messages_dir

    makemessages = "django-admin.py makemessages -l en"
    ignores = " ".join('--ignore="{}/*"'.format(d) for d in CONFIGURATION.ignore_dirs)
    if ignores:
        makemessages += " " + ignores

    # Extract strings from mako templates.
    babel_mako_cmd = 'pybabel extract -F %s -c "Translators:" . -o %s' % (BABEL_CONFIG, BABEL_OUT)
    execute(babel_mako_cmd, working_directory=BASE_DIR)

    # Extract strings from django source files, including .py files.
    make_django_cmd = makemessages + ' --extension html'
    execute(make_django_cmd, working_directory=BASE_DIR)

    # Extract strings from Javascript source files.
    make_djangojs_cmd = makemessages + ' -d djangojs --extension js'
    execute(make_djangojs_cmd, working_directory=BASE_DIR)

    # makemessages creates 'django.po'. This filename is hardcoded.
    # Rename it to django-partial.po to enable merging into django.po later.
    os.rename(
        source_msgs_dir.joinpath('django.po'),
        source_msgs_dir.joinpath('django-partial.po')
    )

    # Segment the generated files.
    segmented_files = segment_pofiles("en")

    # Finish each file.
    for filename in segmented_files:
        LOG.info('Cleaning %s' % filename)
        po = pofile(source_msgs_dir.joinpath(filename))
        # replace default headers with edX headers
        fix_header(po)
        # replace default metadata with edX metadata
        fix_metadata(po)
        # remove key strings which belong in messages.po
        strip_key_strings(po)
        po.save()


def fix_header(po):
    """
    Replace default headers with edX headers
    """

    # By default, django-admin.py makemessages creates this header:
    #
    #   SOME DESCRIPTIVE TITLE.
    #   Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
    #   This file is distributed under the same license as the PACKAGE package.
    #   FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.

    po.metadata_is_fuzzy = []   # remove [u'fuzzy']
    header = po.header
    fixes = (
        ('SOME DESCRIPTIVE TITLE', 'edX translation file\n' + SOURCE_WARN),
        ('Translations template for PROJECT.', 'edX translation file\n' + SOURCE_WARN),
        ('YEAR', '%s' % datetime.utcnow().year),
        ('ORGANIZATION', 'edX'),
        ("THE PACKAGE'S COPYRIGHT HOLDER", "EdX"),
        ('This file is distributed under the same license as the PROJECT project.',
         'This file is distributed under the GNU AFFERO GENERAL PUBLIC LICENSE.'),
        ('This file is distributed under the same license as the PACKAGE package.',
         'This file is distributed under the GNU AFFERO GENERAL PUBLIC LICENSE.'),
        ('FIRST AUTHOR <EMAIL@ADDRESS>',
         'EdX Team <info@edx.org>')
        )
    for src, dest in fixes:
        header = header.replace(src, dest)
    po.header = header

def fix_metadata(po):
    """
    Replace default metadata with edX metadata
    """

    # By default, django-admin.py makemessages creates this metadata:
    #
    #   {u'PO-Revision-Date': u'YEAR-MO-DA HO:MI+ZONE',
    #   u'Language': u'',
    #   u'Content-Transfer-Encoding': u'8bit',
    #   u'Project-Id-Version': u'PACKAGE VERSION',
    #   u'Report-Msgid-Bugs-To': u'',
    #   u'Last-Translator': u'FULL NAME <EMAIL@ADDRESS>',
    #   u'Language-Team': u'LANGUAGE <LL@li.org>',
    #   u'POT-Creation-Date': u'2013-04-25 14:14-0400',
    #   u'Content-Type': u'text/plain; charset=UTF-8',
    #   u'MIME-Version': u'1.0'}

    fixes = {
        'PO-Revision-Date': datetime.utcnow(),
        'Report-Msgid-Bugs-To': 'openedx-translation@googlegroups.com',
        'Project-Id-Version': '0.1a',
        'Language' : 'en',
        'Last-Translator' : '',
        'Language-Team': 'openedx-translation <openedx-translation@googlegroups.com>',
    }
    po.metadata.update(fixes)

def strip_key_strings(po):
    """
    Removes all entries in PO which are key strings.
    These entries should appear only in messages.po, not in any other po files.
    """
    newlist = [entry for entry in po if not is_key_string(entry.msgid)]
    del po[:]
    po += newlist

def is_key_string(string):
    """
    returns True if string is a key string.
    Key strings begin with underscore.
    """
    return len(string) > 1 and string[0] == '_'

if __name__ == '__main__':
    main()
