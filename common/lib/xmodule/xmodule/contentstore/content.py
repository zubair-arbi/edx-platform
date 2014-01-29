XASSET_LOCATION_TAG = 'c4x'
XASSET_SRCREF_PREFIX = 'xasset:'

XASSET_THUMBNAIL_TAIL_NAME = '.jpg'

import os
import logging
import StringIO
from urlparse import urlparse, urlunparse

from xmodule.modulestore import Location
from .django import contentstore
from PIL import Image


class StaticContent(object):
    def __init__(self, loc, name, content_type, data, last_modified_at=None, thumbnail_location=None, import_path=None,
                 length=None, locked=False):
        self.location = loc
        self.name = name  # a display string which can be edited, and thus not part of the location which needs to be fixed
        self.content_type = content_type
        self._data = data
        self.length = length
        self.last_modified_at = last_modified_at
        self.thumbnail_location = Location(thumbnail_location) if thumbnail_location is not None else None
        # optional information about where this file was imported from. This is needed to support import/export
        # cycles
        self.import_path = import_path
        self.locked = locked

    @property
    def is_thumbnail(self):
        return self.location.category == 'thumbnail'

    @staticmethod
    def generate_thumbnail_name(original_name):
        return ('{0}' + XASSET_THUMBNAIL_TAIL_NAME).format(os.path.splitext(original_name)[0])

    @staticmethod
    def compute_location(org, course, name, revision=None, is_thumbnail=False):
        name = name.replace('/', '_')
        return Location([XASSET_LOCATION_TAG, org, course, 'asset' if not is_thumbnail else 'thumbnail',
                         Location.clean_keeping_underscores(name), revision])

    def get_id(self):
        return StaticContent.get_id_from_location(self.location)

    def get_url_path(self):
        return StaticContent.get_url_path_from_location(self.location)

    @property
    def data(self):
        return self._data

    @staticmethod
    def get_url_path_from_location(location):
        if location is not None:
            return u"/{tag}/{org}/{course}/{category}/{name}".format(**location.dict())
        else:
            return None

    @staticmethod
    def is_c4x_path(path_string):
        """
        Returns a boolean if a path is believed to be a c4x link based on the leading element
        """
        return path_string.startswith('/{0}/'.format(XASSET_LOCATION_TAG))

    @staticmethod
    def renamespace_c4x_path(path_string, target_location):
        """
        Returns an updated string which incorporates a new org/course in order to remap an asset path
        to a new namespace
        """
        location = StaticContent.get_location_from_path(path_string)
        location = location.replace(org=target_location.org, course=target_location.course)
        return StaticContent.get_url_path_from_location(location)

    @staticmethod
    def get_static_path_from_location(location):
        """
        This utility static method will take a location identifier and create a 'durable' /static/.. URL representation of it.
        This link is 'durable' as it can maintain integrity across cloning of courseware across course-ids, e.g. reruns of
        courses.
        In the LMS/CMS, we have runtime link-rewriting, so at render time, this /static/... format will get translated into
        the actual /c4x/... path which the client needs to reference static content
        """
        if location is not None:
            return "/static/{name}".format(**location.dict())
        else:
            return None

    @staticmethod
    def get_base_url_path_for_course_assets(loc):
        if loc is not None:
            return "/c4x/{org}/{course}/asset".format(**loc.dict())

    @staticmethod
    def get_id_from_location(location):
        return {'tag': location.tag, 'org': location.org, 'course': location.course,
                'category': location.category, 'name': location.name,
                'revision': location.revision}

    @staticmethod
    def get_location_from_path(path):
        # remove leading / character if it is there one
        if path.startswith('/'):
            path = path[1:]

        return Location(path.split('/'))

    @staticmethod
    def get_id_from_path(path):
        return get_id_from_location(get_location_from_path(path))

    @staticmethod
    def convert_legacy_static_url(path, course_namespace):
        loc = StaticContent.compute_location(course_namespace.org, course_namespace.course, path)
        return StaticContent.get_url_path_from_location(loc)

    @staticmethod
    def convert_legacy_static_url_with_course_id(path, course_id):
        """
        Returns a path to a piece of static content when we are provided with a filepath and
        a course_id
        """
        org, course_num, __ = course_id.split("/")

        # Generate url of urlparse.path component
        scheme, netloc, orig_path, params, query, fragment = urlparse(path)
        loc = StaticContent.compute_location(org, course_num, orig_path)
        loc_url = StaticContent.get_url_path_from_location(loc)

        # Reconstruct with new path
        return urlunparse((scheme, netloc, loc_url, params, query, fragment))

    def stream_data(self):
        yield self._data


class StaticContentStream(StaticContent):
    def __init__(self, loc, name, content_type, stream, last_modified_at=None, thumbnail_location=None, import_path=None,
                 length=None, locked=False):
        super(StaticContentStream, self).__init__(loc, name, content_type, None, last_modified_at=last_modified_at,
                                                  thumbnail_location=thumbnail_location, import_path=import_path,
                                                  length=length, locked=locked)
        self._stream = stream

    def stream_data(self):
        while True:
            chunk = self._stream.read(1024)
            if len(chunk) == 0:
                break
            yield chunk

    def close(self):
        self._stream.close()

    def copy_to_in_mem(self):
        self._stream.seek(0)
        content = StaticContent(self.location, self.name, self.content_type, self._stream.read(),
                                last_modified_at=self.last_modified_at, thumbnail_location=self.thumbnail_location,
                                import_path=self.import_path, length=self.length, locked=self.locked)
        return content


class ContentStore(object):
    '''
    Abstraction for all ContentStore providers (e.g. MongoDB)
    '''
    def save(self, content):
        raise NotImplementedError

    def find(self, filename):
        raise NotImplementedError

    def get_all_content_for_course(self, location, start=0, maxresults=-1, sort=None):
        '''
        Returns a list of static assets for a course, followed by the total number of assets.
        By default all assets are returned, but start and maxresults can be provided to limit the query.

        The return format is a list of dictionary elements. Example:

            [

            {u'displayname': u'profile.jpg', u'chunkSize': 262144, u'length': 85374,
            u'uploadDate': datetime.datetime(2012, 10, 3, 5, 41, 54, 183000), u'contentType': u'image/jpeg',
            u'_id': {u'category': u'asset', u'name': u'profile.jpg', u'course': u'6.002x', u'tag': u'c4x',
            u'org': u'MITx', u'revision': None}, u'md5': u'36dc53519d4b735eb6beba51cd686a0e'},

            {u'displayname': u'profile.thumbnail.jpg', u'chunkSize': 262144, u'length': 4073,
            u'uploadDate': datetime.datetime(2012, 10, 3, 5, 41, 54, 196000), u'contentType': u'image/jpeg',
            u'_id': {u'category': u'asset', u'name': u'profile.thumbnail.jpg', u'course': u'6.002x', u'tag': u'c4x',
            u'org': u'MITx', u'revision': None}, u'md5': u'ff1532598830e3feac91c2449eaa60d6'},

            ....

            ]
        '''
        raise NotImplementedError

    def generate_thumbnail(self, content, tempfile_path=None):
        thumbnail_content = None
        # use a naming convention to associate originals with the thumbnail
        thumbnail_name = StaticContent.generate_thumbnail_name(content.location.name)

        thumbnail_file_location = StaticContent.compute_location(content.location.org, content.location.course,
                                                                 thumbnail_name, is_thumbnail=True)

        # if we're uploading an image, then let's generate a thumbnail so that we can
        # serve it up when needed without having to rescale on the fly
        if content.content_type is not None and content.content_type.split('/')[0] == 'image':
            try:
                # use PIL to do the thumbnail generation (http://www.pythonware.com/products/pil/)
                # My understanding is that PIL will maintain aspect ratios while restricting
                # the max-height/width to be whatever you pass in as 'size'
                # @todo: move the thumbnail size to a configuration setting?!?
                if tempfile_path is None:
                    im = Image.open(StringIO.StringIO(content.data))
                else:
                    im = Image.open(tempfile_path)

                # I've seen some exceptions from the PIL library when trying to save palletted
                # PNG files to JPEG. Per the google-universe, they suggest converting to RGB first.
                im = im.convert('RGB')
                size = 128, 128
                im.thumbnail(size, Image.ANTIALIAS)
                thumbnail_file = StringIO.StringIO()
                im.save(thumbnail_file, 'JPEG')
                thumbnail_file.seek(0)

                # store this thumbnail as any other piece of content
                thumbnail_content = StaticContent(thumbnail_file_location, thumbnail_name,
                                                  'image/jpeg', thumbnail_file)

                contentstore().save(thumbnail_content)

            except Exception, e:
                # log and continue as thumbnails are generally considered as optional
                logging.exception("Failed to generate thumbnail for {0}. Exception: {1}".format(content.location, str(e)))

        return thumbnail_content, thumbnail_file_location
