"""
Provide tests for sysadmin dashboard feature in sysadmin.py
"""

import glob
import os
import shutil
import unittest

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings
from django.utils.html import escape
from django.utils.translation import ugettext as _
import mongoengine

from student.roles import CourseStaffRole, GlobalStaff
from courseware.tests.tests import TEST_DATA_MONGO_MODULESTORE
from dashboard.models import CourseImportLog
from dashboard.sysadmin import Users
from dashboard.git_import import GitImportError
from external_auth.models import ExternalAuthMap
from student.tests.factories import UserFactory
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.xml import XMLModuleStore


TEST_MONGODB_LOG = {
    'host': 'localhost',
    'user': '',
    'password': '',
    'db': 'test_xlog',
}

FEATURES_WITH_SSL_AUTH = settings.FEATURES.copy()
FEATURES_WITH_SSL_AUTH['AUTH_USE_MIT_CERTIFICATES'] = True


class SysadminBaseTestCase(ModuleStoreTestCase):
    """
    Base class with common methods used in XML and Mongo tests
    """

    def setUp(self):
        """Setup test case by adding primary user."""
        super(SysadminBaseTestCase, self).setUp()
        self.user = UserFactory.create(username='test_user',
                                       email='test_user+sysadmin@edx.org',
                                       password='foo')
        self.client = Client()

    def _setstaff_login(self):
        """Makes the test user staff and logs them in"""
        GlobalStaff().add_users(self.user)
        self.client.login(username=self.user.username, password='foo')

    def _add_edx4edx(self):
        """Adds the edx4edx sample course"""
        return self.client.post(reverse('sysadmin_courses'), {
            'repo_location': 'https://github.com/mitocw/edx4edx_lite.git',
            'action': 'add_course', })

    def _rm_edx4edx(self):
        """Deletes the sample course from the XML store"""
        def_ms = modulestore()
        course_path = '{0}/edx4edx_lite'.format(
            os.path.abspath(settings.DATA_DIR))
        try:
            # using XML store
            course = def_ms.courses.get(course_path, None)
        except AttributeError:
            # Using mongo store
            course = def_ms.get_course('MITx/edx4edx/edx4edx')

        # Delete git loaded course
        response = self.client.post(reverse('sysadmin_courses'),
                                {'course_id': course.id,
                                 'action': 'del_course', })
        self.addCleanup(self._rm_glob, '{0}_deleted_*'.format(course_path))

        return response

    def _rm_glob(self, path):
        """
        Create a shell expansion of passed in parameter and iteratively
        remove them.  Must only expand to directories.
        """
        for path in glob.glob(path):
            shutil.rmtree(path)

    def _mkdir(self, path):
        """
        Create directory and add the cleanup for it.
        """
        os.mkdir(path)
        self.addCleanup(shutil.rmtree, path)


@unittest.skipUnless(settings.FEATURES.get('ENABLE_SYSADMIN_DASHBOARD'),
                     "ENABLE_SYSADMIN_DASHBOARD not set")
@override_settings(GIT_IMPORT_WITH_XMLMODULESTORE=True)
class TestSysadmin(SysadminBaseTestCase):
    """
    Test sysadmin dashboard features using XMLModuleStore
    """

    def test_staff_access(self):
        """Test access controls."""

        test_views = ['sysadmin', 'sysadmin_courses', 'sysadmin_staffing', ]
        for view in test_views:
            response = self.client.get(reverse(view))
            self.assertEqual(response.status_code, 302)

        logged_in = self.client.login(username=self.user.username,
                                      password='foo')
        self.assertTrue(logged_in)

        for view in test_views:
            response = self.client.get(reverse(view))
            self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('gitlogs'))
        self.assertEqual(response.status_code, 404)

        self.user.is_staff = True
        self.user.save()

        self.client.logout()
        self.client.login(username=self.user.username, password='foo')

        for view in test_views:
            response = self.client.get(reverse(view))
            self.assertTrue(response.status_code, 200)

        response = self.client.get(reverse('gitlogs'))
        self.assertTrue(response.status_code, 200)

    def test_user_mod(self):
        """Create and delete a user"""

        self._setstaff_login()

        self.client.login(username=self.user.username, password='foo')

        # Create user tests

        # No uname
        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'create_user',
                                     'student_fullname': 'blah',
                                     'student_password': 'foozor', })
        self.assertIn(_('Must provide username'), response.content)
        # no full name
        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'create_user',
                                     'student_uname': 'test_cuser+sysadmin@edx.org',
                                     'student_password': 'foozor', })
        self.assertIn(_('Must provide full name'), response.content)

        # Test create valid user
        self.client.post(reverse('sysadmin'),
                         {'action': 'create_user',
                          'student_uname': 'test_cuser+sysadmin@edx.org',
                          'student_fullname': 'test cuser',
                          'student_password': 'foozor', })

        self.assertIsNotNone(
            User.objects.get(username='test_cuser+sysadmin@edx.org',
                             email='test_cuser+sysadmin@edx.org'))

        # login as new user to confirm
        self.assertTrue(self.client.login(
            username='test_cuser+sysadmin@edx.org', password='foozor'))

        self.client.logout()
        self.client.login(username=self.user.username, password='foo')

        # Delete user tests

        # Try no username
        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'del_user', })
        self.assertIn(_('Must provide username'), response.content)

        # Try bad usernames
        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'del_user',
                                     'student_uname': 'flabbergast@example.com',
                                     'student_fullname': 'enigma jones', })
        self.assertIn(_('Cannot find user with email address'), response.content)

        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'del_user',
                                     'student_uname': 'flabbergast',
                                     'student_fullname': 'enigma jones', })
        self.assertIn(_('Cannot find user with username'), response.content)

        self.client.post(reverse('sysadmin'),
                         {'action': 'del_user',
                          'student_uname': 'test_cuser+sysadmin@edx.org',
                          'student_fullname': 'test cuser', })

        self.assertEqual(0, len(User.objects.filter(
            username='test_cuser+sysadmin@edx.org',
            email='test_cuser+sysadmin@edx.org')))

        self.assertEqual(1, len(User.objects.all()))

    def test_user_csv(self):
        """Download and validate user CSV"""

        num_test_users = 100
        self._setstaff_login()

        # Stuff full of users to test streaming
        for user_num in xrange(num_test_users):
            Users().create_user('testingman_with_long_name{}'.format(user_num),
                                'test test')

        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'download_users', })

        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual('text/csv', response['Content-Type'])
        self.assertIn('test_user', response.content)
        self.assertTrue(num_test_users + 2, len(response.content.splitlines()))

        # Clean up
        User.objects.filter(
            username__startswith='testingman_with_long_name').delete()

    @override_settings(FEATURES=FEATURES_WITH_SSL_AUTH)
    def test_authmap_repair(self):
        """Run authmap check and repair"""

        self._setstaff_login()

        Users().create_user('test0', 'test test')
        # Will raise exception, so no assert needed
        eamap = ExternalAuthMap.objects.get(external_name='test test')
        mitu = User.objects.get(username='test0')

        self.assertTrue(check_password(eamap.internal_password, mitu.password))
        mitu.set_password('not autogenerated')
        mitu.save()
        self.assertFalse(check_password(eamap.internal_password, mitu.password))

        # Create really non user AuthMap
        ExternalAuthMap(external_id='ll',
                        external_domain='ll',
                        external_credentials='{}',
                        external_email='a@b.c',
                        external_name='c',
                        internal_password='').save()

        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'repair_eamap', })

        self.assertIn('{0} test0'.format(_('Failed in authenticating')),
                      response.content)
        self.assertIn(_('fixed password'), response.content)

        self.assertTrue(self.client.login(username='test0',
                                          password=eamap.internal_password))

        # Check for all OK
        self._setstaff_login()
        response = self.client.post(reverse('sysadmin'),
                                    {'action': 'repair_eamap', })
        self.assertIn(_('All ok!'), response.content)

    def test_xml_course_add_delete(self):
        """add and delete course from xml module store"""

        self._setstaff_login()

        # Try bad git repo
        response = self.client.post(reverse('sysadmin_courses'), {
            'repo_location': 'github.com/mitocw/edx4edx_lite',
            'action': 'add_course', })
        self.assertIn(_("The git repo location should end with '.git', "
                        "and be a valid url"), response.content.decode('utf-8'))

        response = self.client.post(reverse('sysadmin_courses'), {
            'repo_location': 'http://example.com/not_real.git',
            'action': 'add_course', })
        self.assertIn(_('Unable to clone or pull repository'),
                      response.content.decode('utf-8'))
        # Create git loaded course
        response = self._add_edx4edx()

        def_ms = modulestore()
        self.assertIn('xml', str(def_ms.__class__))
        course = def_ms.courses.get('{0}/edx4edx_lite'.format(
            os.path.abspath(settings.DATA_DIR)), None)
        self.assertIsNotNone(course)

        # Delete a course
        response = self._rm_edx4edx()
        course = def_ms.courses.get('{0}/edx4edx_lite'.format(
            os.path.abspath(settings.DATA_DIR)), None)
        self.assertIsNone(course)

        # Try and delete a non-existent course
        response = self.client.post(reverse('sysadmin_courses'),
                                    {'course_id': 'foobar/foo/blah',
                                     'action': 'del_course', })
        self.assertIn(_('Error - cannot get course with ID'),
                      response.content.decode('utf-8'))

    @override_settings(GIT_IMPORT_WITH_XMLMODULESTORE=False)
    def test_xml_safety_flag(self):
        """Make sure the settings flag to disable xml imports is working"""

        self._setstaff_login()
        response = self._add_edx4edx()
        self.assertIn('GIT_IMPORT_WITH_XMLMODULESTORE', response.content)

        def_ms = modulestore()
        course = def_ms.courses.get('{0}/edx4edx_lite'.format(
            os.path.abspath(settings.DATA_DIR)), None)
        self.assertIsNone(course)

    def test_git_pull(self):
        """Make sure we can pull"""

        self._setstaff_login()

        response = self._add_edx4edx()
        response = self._add_edx4edx()
        self.assertIn(_("The course {0} already exists in the data directory! "
                        "(reloading anyway)").format('edx4edx_lite'),
                      response.content.decode('utf-8'))
        self._rm_edx4edx()

    def test_staff_csv(self):
        """Download and validate staff CSV"""

        self._setstaff_login()
        self._add_edx4edx()

        def_ms = modulestore()
        course = def_ms.get_course('MITx/edx4edx/edx4edx')
        CourseStaffRole(course.location).add_users(self.user)

        response = self.client.post(reverse('sysadmin_staffing'),
                                    {'action': 'get_staff_csv', })
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual('text/csv', response['Content-Type'])
        columns = [_('course_id'), _('role'), _('username'),
                   _('email'), _('full_name'), ]
        self.assertIn(','.join('"' + c + '"' for c in columns),
                      response.content)

        self._rm_edx4edx()

    def test_enrollment_page(self):
        """
        Adds a course and makes sure that it shows up on the staffing and
        enrollment page
        """

        self._setstaff_login()
        self._add_edx4edx()
        response = self.client.get(reverse('sysadmin_staffing'))
        self.assertIn('edx4edx', response.content)
        self._rm_edx4edx()


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
@override_settings(MONGODB_LOG=TEST_MONGODB_LOG)
@unittest.skipUnless(settings.FEATURES.get('ENABLE_SYSADMIN_DASHBOARD'),
                     "ENABLE_SYSADMIN_DASHBOARD not set")
class TestSysAdminMongoCourseImport(SysadminBaseTestCase):
    """
    Check that importing into the mongo module store works
    """

    @classmethod
    def tearDownClass(cls):
        """Delete mongo log entries after test."""
        super(TestSysAdminMongoCourseImport, cls).tearDownClass()
        try:
            mongoengine.connect(TEST_MONGODB_LOG['db'])
            CourseImportLog.objects.all().delete()
        except mongoengine.connection.ConnectionError:
            pass

    def _setstaff_login(self):
        """
        Makes the test user staff and logs them in
        """

        self.user.is_staff = True
        self.user.save()

        self.client.login(username=self.user.username, password='foo')

    def test_missing_repo_dir(self):
        """
        Ensure that we handle a missing repo dir
        """

        self._setstaff_login()

        if os.path.isdir(getattr(settings, 'GIT_REPO_DIR')):
            shutil.rmtree(getattr(settings, 'GIT_REPO_DIR'))

        # Create git loaded course
        response = self._add_edx4edx()
        self.assertIn(GitImportError.NO_DIR,
                      response.content.decode('UTF-8'))

    def test_mongo_course_add_delete(self):
        """
        This is the same as TestSysadmin.test_xml_course_add_delete,
        but it uses a mongo store
        """

        self._setstaff_login()
        self._mkdir(getattr(settings, 'GIT_REPO_DIR'))

        def_ms = modulestore()
        self.assertFalse(isinstance(def_ms, XMLModuleStore))

        self._add_edx4edx()
        course = def_ms.get_course('MITx/edx4edx/edx4edx')
        self.assertIsNotNone(course)

        self._rm_edx4edx()
        course = def_ms.get_course('MITx/edx4edx/edx4edx')
        self.assertIsNone(course)

    def test_gitlogs(self):
        """
        Create a log entry and make sure it exists
        """

        self._setstaff_login()
        self._mkdir(getattr(settings, 'GIT_REPO_DIR'))

        self._add_edx4edx()
        response = self.client.get(reverse('gitlogs'))

        # Check that our earlier import has a log with a link to details
        self.assertIn('/gitlogs/MITx/edx4edx/edx4edx', response.content)

        response = self.client.get(
            reverse('gitlogs_detail', kwargs={
                'course_id': 'MITx/edx4edx/edx4edx'}))

        self.assertIn('======&gt; IMPORTING course to location',
                      response.content)

        self._rm_edx4edx()

    def test_gitlog_bad_course(self):
        """
        Make sure we gracefully handle courses that don't exist.
        """
        self._setstaff_login()
        response = self.client.get(
            reverse('gitlogs_detail', kwargs={
                'course_id': 'Not/Real/Testing'}))
        self.assertEqual(404, response.status_code)

    def test_gitlog_courseteam_access(self):
        """
        Ensure course team users are allowed to access only their own course.
        """

        self._mkdir(getattr(settings, 'GIT_REPO_DIR'))

        self._setstaff_login()
        self._add_edx4edx()
        self.user.is_staff = False
        self.user.save()
        logged_in = self.client.login(username=self.user.username,
                                      password='foo')
        response = self.client.get(reverse('gitlogs'))
        # Make sure our non privileged user doesn't have access to all logs
        self.assertEqual(response.status_code, 404)
        # Or specific logs
        response = self.client.get(reverse('gitlogs_detail', kwargs={
            'course_id': 'MITx/edx4edx/edx4edx'}))
        self.assertEqual(response.status_code, 404)

        # Add user as staff in course team
        def_ms = modulestore()
        course = def_ms.get_course('MITx/edx4edx/edx4edx')
        CourseStaffRole(course.location).add_users(self.user)

        self.assertTrue(CourseStaffRole(course.location).has_user(self.user))
        logged_in = self.client.login(username=self.user.username,
                                      password='foo')
        self.assertTrue(logged_in)

        response = self.client.get(
            reverse('gitlogs_detail', kwargs={
                'course_id': 'MITx/edx4edx/edx4edx'}))
        self.assertIn('======&gt; IMPORTING course to location',
                      response.content)

        self._rm_edx4edx()
