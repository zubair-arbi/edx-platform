import string
import random
import collections

from django.test import TestCase
from mock import MagicMock
from django.test.utils import override_settings                       
import django.core.urlresolvers as urlresolvers

import django_comment_client.mustache_helpers as mustache_helpers

#########################################################################################

class PluralizeTest(TestCase):

    def setUp(self):
        self.text1 = '0 goat'
        self.text2 = '1 goat'
        self.text3 = '7 goat'
        self.content = 'unused argument'

    def test_pluralize(self):
        self.assertEqual(mustache_helpers.pluralize(self.content, self.text1), 'goats')
        self.assertEqual(mustache_helpers.pluralize(self.content, self.text2), 'goat')
        self.assertEqual(mustache_helpers.pluralize(self.content, self.text3), 'goats')
  
#########################################################################################

class UrlForUserTest(TestCase):

    def setUp(self):

        self.content = {'course_id':'edX/full/6.002_Spring_2012'}
        self.user_id = 'jnater'
    
    @override_settings(MITX_FEATURES = {'ENABLE_DISCUSSION_SERVICE':True})
    def test_url_for_user(self):

        self.assertEqual(urlresolvers.resolve(mustache_helpers.url_for_user(self.content, 
                                                                            self.user_id)).url_name,
                         "user_profile")

#########################################################################################

class UrlForTagsTest(TestCase):

    def setUp(self):

        self.content = {'course_id':'edX/full/6.002_Spring_2012'}
        self.tags = u'a, b, c'

    @override_settings(MITX_FEATURES = {'ENABLE_DISCUSSION_SERVICE':True})
    def test_url_for_tags(self):

        self.assertEqual(urlresolvers.resolve(mustache_helpers.url_for_tags(self.content, 
                                                                            self.tags)).url_name, 
                         "forum_form_discussion")

#########################################################################################
		
class CloseThreadTextTest(TestCase):

    def setUp(self):
        self.contentClosed = {'closed': True}
        self.contentOpen = {'closed': False}

    def test_close_thread_text(self):
        self.assertEqual(mustache_helpers.close_thread_text(self.contentClosed), 'Re-open thread')
        self.assertEqual(mustache_helpers.close_thread_text(self.contentOpen), 'Close thread')


