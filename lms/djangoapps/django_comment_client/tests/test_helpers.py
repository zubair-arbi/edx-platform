import string
import random
import collections

from django.test import TestCase                         

import django_comment_client.helpers as helpers

class PluralizeTestCase(TestCase):

    def setUp(self):
	self.term = "cat"

    def testPluralize(self):
        self.assertEqual(pluralize(self.term, 0), "cats")
        self.assertEqual(pluralize(self.term, 1), "cat")
        self.assertEqual(pluralize(self.term, 2), "cats")

#class RenderContentTestCase(TestCase):
#	
#	def setUp(self):
#		self.
       

