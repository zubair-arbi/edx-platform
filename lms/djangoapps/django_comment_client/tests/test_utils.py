import string
import random
import collections

from django.contrib.auth.models import User
from django.test import TestCase                         

import student.models
import django_comment_client.models as models
import django_comment_client.utils as utils

import xmodule.modulestore.django as django

#########################################################################################

class UtilsTestCase(TestCase):
    def random_str(self, length=15, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(length)) 

    def setUp(self):
        self.dic1 = {}
        self.dic2 = {}
        self.dic2none = {}
        self.dic2blank = {}

        self.dic1["cats"] = "meow"
        self.dic1["dogs"] = "woof"
        self.dic1keys = ["cats", "dogs", "hamsters"]

        self.dic2["lions"] = "roar"
        self.dic2["ducks"] = "quack"
        
        self.dic2none["lions"] = "roar"
        self.dic2none["ducks"] = "quack"
        self.dic2none["seaweed"] = None

        self.dic2blank["lions"] = "roar"
        self.dic2blank["ducks"] = "quack"
        self.dic2blank["whales"] = ""   

        self.course_id = "edX/toy/2012_Fall"

        self.moderator_role = models.Role.objects.get_or_create(name="Moderator", course_id=self.course_id)[0]
        self.student_role = models.Role.objects.get_or_create(name="Student", course_id=self.course_id)[0]

        self.student = User.objects.create(username=self.random_str(),
                            password="123456", email="john@yahoo.com")
        self.moderator = User.objects.create(username=self.random_str(),
                            password="123456", email="staff@edx.org")
        self.moderator.is_staff = True
        self.moderator.save()
        self.student_enrollment = student.models.CourseEnrollment.objects.create(user=self.student, course_id=self.course_id)
        self.moderator_enrollment = student.models.CourseEnrollment.objects.create(user=self.moderator, course_id=self.course_id)
        self.course = "6.006"

    def test_extract(self):
        test_extract_dic1 = {"cats": "meow", "dogs": "woof", "hamsters": None}
        self.assertEqual(utils.extract(self.dic1, self.dic1keys), test_extract_dic1)

    def test_strip_none(self):
        self.assertEqual(utils.strip_none(self.dic2none), self.dic2)

    def test_strip_blank(self):
        self.assertEqual(utils.strip_blank(self.dic2blank), self.dic2)

    def test_merge_dic(self):
        self.dicMerge12 ={'cats': 'meow', 'dogs': 'woof','lions': 'roar','ducks': 'quack'}
        self.assertEqual(utils.merge_dict(self.dic1, self.dic2), self.dicMerge12)

    def test_get_role_ids(self):
        self.assertEqual(utils.get_role_ids(self.course_id), {u'Moderator': [2], u'Student': [1], 'Staff': [2]})

    def test_get_full_modules(self):
        _FULLMODULES = True
        self.assertTrue(utils.get_full_modules())
        _FULLMODULES = False
        self.assertEqual(utils.get_full_modules(), django.modulestore().modules)


    ##needs work
    #def test_get_discussion_id_map(self):
    #    _DISCUSSIONINFO = collections.defaultdict(list,[("6.006", False), ("18.410", True)])


