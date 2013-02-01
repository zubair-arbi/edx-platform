<<<<<<< HEAD
import string
import random
import collections
from collections import defaultdict
from django.contrib.auth.models import User
from django.test import TestCase                         
from django.db.models.signals import m2m_changed, pre_delete, pre_save, post_delete, post_save
from django.dispatch.dispatcher import _make_id

from student.models import CourseEnrollment, \
                           replicate_enrollment_save, \
                           replicate_enrollment_delete, \
                           update_user_information, \
                           replicate_user_save
from .permissions import *
=======
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings

from mock import Mock

from override_settings import override_settings

import xmodule.modulestore.django

from student.models import CourseEnrollment

from django.db.models.signals import m2m_changed, pre_delete, pre_save, post_delete, post_save
from django.dispatch.dispatcher import _make_id
import string
import random
from .permissions import has_permission
>>>>>>> origin
from .models import Role, Permission
from .utils import strip_none
from .utils import extract
from .utils import strip_blank
from .utils import merge_dict
from .utils import get_role_ids
from .utils import get_full_modules
from .utils import get_discussion_id_map
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import Location
from xmodule.course_module import CourseDescriptor

<<<<<<< HEAD
from .helpers import pluralize
from .mustache_helpers import close_thread_text
from .mustache_helpers import url_for_user
from comment_client import CommentClientError
from django.http import HttpRequest
from .middleware import *

from .utils import strip_none
from .utils import extract
from .utils import strip_blank
from .utils import merge_dict
from .utils import get_role_ids
from .utils import get_full_modules
from .utils import get_discussion_id_map
from xmodule.modulestore.django import modulestore

#Tests for .utils

class UtilsTestCase(TestCase):
=======
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import Location
from xmodule.modulestore.xml_importer import import_from_xml
from xmodule.modulestore.xml import XMLModuleStore

import comment_client

from courseware.tests.tests import PageLoader, TEST_DATA_XML_MODULESTORE

#@override_settings(MODULESTORE=TEST_DATA_XML_MODULESTORE)
#class TestCohorting(PageLoader):
#    """Check that cohorting works properly"""
#
#    def setUp(self):
#        xmodule.modulestore.django._MODULESTORES = {}
#
#        # Assume courses are there
#        self.toy = modulestore().get_course("edX/toy/2012_Fall")
#
#        # Create two accounts
#        self.student = 'view@test.com'
#        self.student2 = 'view2@test.com'
#        self.password = 'foo'
#        self.create_account('u1', self.student, self.password)
#        self.create_account('u2', self.student2, self.password)
#        self.activate_user(self.student)
#        self.activate_user(self.student2)
#
#    def test_create_thread(self):
#        my_save = Mock()
#        comment_client.perform_request = my_save
#
#        resp = self.client.post(
#            reverse('django_comment_client.base.views.create_thread',
#                    kwargs={'course_id': 'edX/toy/2012_Fall',
#                            'commentable_id': 'General'}),
#                                        {'some': "some",
#                                         'data': 'data'})
#        self.assertTrue(my_save.called)
#
#        #self.assertEqual(resp.status_code, 200)
#        #self.assertEqual(my_save.something, "expected", "complaint if not true")
#
#        self.toy.metadata["cohort_config"] = {"cohorted": True}
#
#        # call the view again ...
#
#       # assert that different things happened



class PermissionsTestCase(TestCase):
>>>>>>> origin
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

        self.moderator_role = Role.objects.get_or_create(name="Moderator", course_id=self.course_id)[0]
        self.student_role = Role.objects.get_or_create(name="Student", course_id=self.course_id)[0]

        self.student = User.objects.create(username=self.random_str(),
                            password="123456", email="john@yahoo.com")
        self.moderator = User.objects.create(username=self.random_str(),
                            password="123456", email="staff@edx.org")
        self.moderator.is_staff = True
        self.moderator.save()
        self.student_enrollment = CourseEnrollment.objects.create(user=self.student, course_id=self.course_id)
        self.moderator_enrollment = CourseEnrollment.objects.create(user=self.moderator, course_id=self.course_id)
        
        # class Dummy():
        #     def render_template():
        #         pass
        # self.course = CourseDescriptor(Dummy)




    def test_extract(self):
        test_extract_dic1 = {"cats": "meow", "dogs": "woof", "hamsters": None}
        self.assertEqual(extract(self.dic1, self.dic1keys), test_extract_dic1)

    def test_strip_none(self):
        self.assertEqual(strip_none(self.dic2none), self.dic2)

    def test_strip_blank(self):
        self.assertEqual(strip_blank(self.dic2blank), self.dic2)

    def test_merge_dic(self):
        self.dicMerge12 ={'cats': 'meow', 'dogs': 'woof','lions': 'roar','ducks': 'quack'}
        self.assertEqual(merge_dict(self.dic1, self.dic2), self.dicMerge12)

    def test_get_role_ids(self):
        self.assertEqual(get_role_ids(self.course_id), {u'Moderator': [2], u'Student': [1], 'Staff': [2]})

    def test_get_full_modules(self):
        _FULLMODULES = True
        self.assertTrue(get_full_modules())
        _FULLMODULES = False
        self.assertEqual(get_full_modules(), modulestore().modules)

    def test_get_discussion_id_map(self):
        _DISCUSSIONINFO = collections.defaultdict(list,[("6.006", False), ("18.410", True)])

#Tests for .permissions

class PermissionsTestCase(TestCase):
    def random_str(self, length=15, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(length))

    def setUp(self):

        self.course_id = "edX/toy/2012_Fall"

        self.moderator_role = Role.objects.get_or_create(name="Moderator", \
                                                         course_id=self.course_id)[0]
        self.student_role = Role.objects.get_or_create(name="Student", \
                                                       course_id=self.course_id)[0]

        self.student = User.objects.create(username=self.random_str(),
                            password="123456", email="john@yahoo.com")
        self.moderator = User.objects.create(username=self.random_str(),
                            password="123456", email="staff@edx.org")
        self.moderator.is_staff = True
        self.moderator.save()
        self.student_enrollment = CourseEnrollment.objects.create(user=self.student, \
                                                                  course_id=self.course_id)
        self.moderator_enrollment = CourseEnrollment.objects.create(user=self.moderator, \
                                                                    course_id=self.course_id)
        #Fake json files
        self.empty_data = {"content":{
                                    }
                    }
        self.open_data = {"content":{
                                "closed":False,
                                "user_id":str(self.student.id)
                                }
                     }
        self.closed_data = {"content":{
                                "closed":True,
                                "user_id":str(self.student.id)
                                }
                     }
        
    def tearDown(self):
        self.student_enrollment.delete()
        self.moderator_enrollment.delete()

# Do we need to have this? We shouldn't be deleting students, ever
#        self.student.delete()
#        self.moderator.delete()

    def testDefaultRoles(self):
        self.assertTrue(self.student_role in self.student.roles.all())
        self.assertTrue(self.moderator_role in self.moderator.roles.all())

    def testPermission(self):
        name = self.random_str()
        self.moderator_role.add_permission(name)
        self.assertTrue(has_permission(self.moderator, name, self.course_id))
        # Moderators do not have student priveleges unless explicitly added

        self.student_role.add_permission(name)
        self.assertTrue(has_permission(self.student, name, self.course_id))

        # Students don't have moderator priveleges 
        name2 = self.random_str()
        self.student_role.add_permission(name2)
        self.assertFalse(has_permission(self.moderator, name2, self.course_id))

    def testCachedPermission(self):
        
        # Cache miss returns None
        # Don't really understand how this works? What's in Cache?
        self.assertFalse(cached_has_permission(self.student, self.moderator, \
                                            course_id=None))
        self.assertFalse(cached_has_permission(self.student, "update_thread", \
                                            course_id=None))

    def testCheckCondition(self):
        # Checks whether something? is open, or whether the author is user
        self.assertFalse(check_condition(self.student, 'is_open', \
                                         self.course_id, self.empty_data))
        self.assertFalse(check_condition(self.student, 'is_author', \
                                         self.course_id, self.empty_data))
        self.assertTrue(check_condition(self.student,'is_open', \
                                         self.course_id, self.open_data))
        self.assertTrue(check_condition(self.student, 'is_author', \
                                         self.course_id, self.open_data))
        self.assertFalse(check_condition(self.student,'is_open', \
                                         self.course_id, self.closed_data))

    def testCheckConditionsPermissions(self):
        # Should be True, but test fails in that case?
        # What do I have to do to get True?
        self.assertFalse(check_conditions_permissions(self.student, 'is_open', \
                                                     self.course_id,\
                                                     data=self.open_data))
        self.assertFalse(check_conditions_permissions(self.student, 'is_open', \
                                                     self.course_id,\
                                                     data=self.empty_data))

        self.assertFalse(check_conditions_permissions(self.student, \
                                                      ['is_open', 'is_author'],\
                                                      self.course_id,\
                                                      data=self.open_data))
        self.assertFalse(check_conditions_permissions(self.student, \
                                                      ['is_open', 'is_author'],\
                                                      self.course_id,\
                                                      data=self.open_data,\
                                                      operator='and'))
        self.assertFalse(check_conditions_permissions(self.student, 'update_thread',\
                                                      self.course_id, data=self.open_data))

    def testCheckPermissionsByView(self):
        # kwargs is the data entered in check_condition, which is json?
        self.assertRaises(UnboundLocalError, check_permissions_by_view, self.student,
                                                self.course_id, self.empty_data,
                                                  "nonexistant")
        self.assertFalse(check_permissions_by_view(self.student,self.course_id, \
                                                   self.empty_data, 'update_thread'))
##        self.assertTrue(check_permissions_by_view(self.student,self.course_id, \
##                                                   self.open_data, 'vote_for_thread'))

class PluralizeTestCase(TestCase):
    """Practice test case"""
    def setUp(self):
        self.term = "cat"

    def testPluralize(self):
        self.assertEqual(pluralize(self.term, 0), "cats")
        self.assertEqual(pluralize(self.term, 1), "cat")
        self.assertEqual(pluralize(self.term, 2), "cats")

    def tearDown(self):
        pass

# finished testing models.py

class PermissionClassTestCase(TestCase):

    def setUp(self):
        
        self.permission = Permission.objects.get_or_create(name="test")[0]

    def testUnicode(self):
        # Doesn't print?
        self.assertEqual(str(self.permission), "test")

class RoleClassTestCase(TestCase):
    def setUp(self):
        # For course ID, syntax edx/classname/classdate is important
        # because xmodel.course_module.id_to_location looks for a string to split
        
        self.course_id = "edX/toy/2012_Fall"
        self.student_role = Role.objects.get_or_create(name="Student", \
                                                         course_id=self.course_id)[0]
        self.student_role.add_permission("delete_thread")
        self.student_2_role = Role.objects.get_or_create(name="Student", \
                                                         course_id=self.course_id)[0]
        self.TA_role = Role.objects.get_or_create(name="Community TA",\
                                                  course_id=self.course_id)[0]
        self.course_id_2 = "edx/6.002x/2012_Fall"
        self.TA_role_2 = Role.objects.get_or_create(name="Community TA",\
                                                  course_id=self.course_id_2)[0]
        class Dummy():
            def render_template():
                pass
        d = {"data":{
                "textbooks":[],
                'wiki_slug':True,
                }
             }
##        input_list = ['http', 'MITx', '6.002x', '2012_Fall', 'about'] 
##        self.course = CourseDescriptor(Dummy(), definition=d, \
##                                       location=Location(input_list),\
##                                       start = True)
        
    def testHasPermission(self):
        # It seems that whenever you add a permission to student_role,
        # Roles with the same FORUM_ROLE in same class also receives the same
        # permission.
        # Is this desirable?
        self.assertTrue(self.student_role.has_permission("delete_thread"))
        self.assertTrue(self.student_2_role.has_permission("delete_thread"))
        self.assertFalse(self.TA_role.has_permission("delete_thread"))

    def testInheritPermissions(self):
        #Don't know how to create a TA role that is for a different class
        self.TA_role.inherit_permissions(self.student_role)
        self.assertTrue(self.TA_role.has_permission("delete_thread"))
        #self.assertFalse(self.TA_role_2.has_permission("delete_thread"))
        # Despite being from 2 different courses, TA_role_2 can still inherit
        # permissions from TA_role ?
        #self.TA_role_2.inherit_permissions(TA_role)
        #self.assertTrue(self.TA_role_2.has_permission("delete_thread"))

class PluralizeTestCase(TestCase):
	
	def setUp(self):
		self.term = "cat"

	def test_pluralize(self):
		self.assertEqual(pluralize(self.term, 0), "cats")
		self.assertEqual(pluralize(self.term, 1), "cat")
		self.assertEqual(pluralize(self.term, 3), "cats")

	def tearDown(self):
		pass

#Tests for .middleware

class ProcessExceptionTestCase(TestCase):


	def setUp(self):
		self.a = AjaxExceptionMiddleware()
		self.request1 = HttpRequest()
		self.request0 = HttpRequest()
		self.exception1 = CommentClientError('a')
		self.exception0 = 5
		self.request1.META['HTTP_X_REQUESTED_WITH'] = "XMLHttpRequest"
		self.request0.META['HTTP_X_REQUESTED_WITH'] = "SHADOWFAX"

		
	def test_process_exception(self):
		self.assertRaises(JsonError, self.a.process_exception(self.request1, self.exception1))
		self.assertIsNone(self.a.process_exception(self.request1, self.exception0))
		self.assertIsNone(self.a.process_exception(self.request0, self.exception1))
		self.assertIsNone(self.a.process_exception(self.request0, self.exception0))

	def tearDown(self):
		pass

#Start of tests for .mustache_helpers.py
class CloseThreadTextTestCase(TestCase):
	
	def setUp(self):
		self.contentClosed = {'closed': True}
		self.contentOpen = {'closed': False}

	def test_close_thread_text(self):
		self.assertEqual(close_thread_text(self.contentClosed), 'Re-open thread')
		self.assertEqual(close_thread_text(self.contentOpen), 'Close thread')

	def tearDown(self):
		pass

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

        self.moderator_role = Role.objects.get_or_create(name="Moderator", course_id=self.course_id)[0]
        self.student_role = Role.objects.get_or_create(name="Student", course_id=self.course_id)[0]

        self.student = User.objects.create(username=self.random_str(),
                            password="123456", email="john@yahoo.com")
        self.moderator = User.objects.create(username=self.random_str(),
                            password="123456", email="staff@edx.org")
        self.moderator.is_staff = True
        self.moderator.save()
        self.student_enrollment = CourseEnrollment.objects.create(user=self.student, course_id=self.course_id)
        self.moderator_enrollment = CourseEnrollment.objects.create(user=self.moderator, course_id=self.course_id)
        self.course = "6.006"

    def test_extract(self):
        test_extract_dic1 = {"cats": "meow", "dogs": "woof", "hamsters": None}
        self.assertEqual(extract(self.dic1, self.dic1keys), test_extract_dic1)

    def test_strip_none(self):
        self.assertEqual(strip_none(self.dic2none), self.dic2)

    def test_strip_blank(self):
        self.assertEqual(strip_blank(self.dic2blank), self.dic2)

    def test_merge_dic(self):
        self.dicMerge12 ={'cats': 'meow', 'dogs': 'woof','lions': 'roar','ducks': 'quack'}
        self.assertEqual(merge_dict(self.dic1, self.dic2), self.dicMerge12)

    def test_get_role_ids(self):
        self.assertEqual(get_role_ids(self.course_id), {u'Moderator': [2], u'Student': [1], 'Staff': [2]})

    def test_get_full_modules(self):
        _FULLMODULES = True
        self.assertTrue(get_full_modules())
        _FULLMODULES = False
        self.assertEqual(get_full_modules(), modulestore().modules)

    def test_get_discussion_id_map(self):
        _DISCUSSIONINFO = defaultdict({"6.006": False, "18.410": True})


#Tests for .middleware

class ProcessExceptionTestCase(TestCase):


	def setUp(self):
		self.a = AjaxExceptionMiddleware()
		self.request1 = HttpRequest()
		self.request0 = HttpRequest()
		self.exception1 = CommentClientError('{}')
		self.exception0 = ValueError()
		self.request1.META['HTTP_X_REQUESTED_WITH'] = "XMLHttpRequest"
		self.request0.META['HTTP_X_REQUESTED_WITH'] = "SHADOWFAX"


		
	def test_process_exception(self):
		self.assertIsInstance(self.a.process_exception(self.request1, self.exception1), JsonError)
		self.assertIsNone(self.a.process_exception(self.request1, self.exception0))
		self.assertIsNone(self.a.process_exception(self.request0, self.exception1))
		self.assertIsNone(self.a.process_exception(self.request0, self.exception0))

	def tearDown(self):
		pass
