import string
import random
import collections

from django.test import TestCase
import django.core.urlresolvers as urlresolvers                       

import django_comment_client.mustache_helpers as mustache_helpers

#########################################################################################
		
class CloseThreadTextTestCase(TestCase):

    def setUp(self):
        self.contentClosed = {'closed': True}
        self.contentOpen = {'closed': False}

    def test_close_thread_text(self):
        self.assertEqual(mustache_helpers.close_thread_text(self.contentClosed), 'Re-open thread')
        self.assertEqual(mustache_helpers.close_thread_text(self.contentOpen), 'Close thread')

#########################################################################################

class PluralizeTestCase(TestCase):

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
    
    def test_url_for_user(self):

        self.assertEqual(urlresolvers.resolve(mustache_helpers.url_for_user(self.content, self.user_id)), 'django_comment_client.forum.views.user_profile')

