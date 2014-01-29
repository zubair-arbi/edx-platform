#!/usr/bin/env python

"""
See https://edx-wiki.atlassian.net/wiki/display/ENG/PO+File+workflow

This task merges and compiles the human-readable .po files on the
local filesystem into machine-readable .mo files. This is typically
necessary as part of the build process since these .mo files are
needed by Django when serving the web app.

The configuration file (in edx-platform/conf/locale/config) specifies which
languages to generate.

"""

import os, sys, logging
from polib import pofile

from i18n.config import BASE_DIR, CONFIGURATION
from i18n.execute import execute

LOG = logging.getLogger(__name__)


def merge(locale, target='django.po', sources=('django-partial.po',), fail_if_missing=True):
    """
    For the given locale, merge the `sources` files to become the `target`
    file.  Note that the target file might also be one of the sources.

    If fail_if_missing is true, and the files to be merged are missing,
    throw an Exception, otherwise return silently.

    If fail_if_missing is false, and the files to be merged are missing,
    just return silently.

    """
    LOG.info('Merging {target} for locale {locale}'.format(target=target, locale=locale))
    locale_directory = CONFIGURATION.get_messages_dir(locale)
    try:
        validate_files(locale_directory, sources)
    except Exception, e:
        if not fail_if_missing:
            return
        raise e

    # merged file is merged.po
    merge_cmd = 'msgcat -o merged.po ' + ' '.join(sources)
    execute(merge_cmd, working_directory=locale_directory)

    # clean up redunancies in the metadata
    merged_filename = locale_directory.joinpath('merged.po')
    clean_metadata(merged_filename)

    # rename merged.po -> django.po (default)
    target_filename = locale_directory.joinpath(target)
    os.rename(merged_filename, target_filename)


def merge_files(locale, fail_if_missing=True):
    """
    Merge all the files in `locale`, as specified in config.yaml.
    """
    for target, sources in CONFIGURATION.generate_merge.items():
        merge(locale, target, sources, fail_if_missing)


def clean_metadata(file):
    """
    Clean up redundancies in the metadata caused by merging.
    """
    # Reading in the .po file and saving it again fixes redundancies.
    pomsgs = pofile(file)
    # The msgcat tool marks the metadata as fuzzy, but it's ok as it is.
    pomsgs.metadata_is_fuzzy = False
    pomsgs.save()


def validate_files(dir, files_to_merge):
    """
    Asserts that the given files exist.
    files_to_merge is a list of file names (no directories).
    dir is the directory (a path object from path.py) in which the files should appear.
    raises an Exception if any of the files are not in dir.
    """
    for path in files_to_merge:
        pathname = dir.joinpath(path)
        if not pathname.exists():
            raise Exception("I18N: Cannot generate because file not found: {0}".format(pathname))


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    for locale in CONFIGURATION.locales:
        merge_files(locale)
    # Dummy text is not required. Don't raise exception if files are missing.
    merge_files(CONFIGURATION.dummy_locale, fail_if_missing=False)

    compile_cmd = 'django-admin.py compilemessages'
    execute(compile_cmd, working_directory=BASE_DIR)


if __name__ == '__main__':
    main()
