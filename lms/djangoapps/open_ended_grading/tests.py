"""
Tests for open ended grading interfaces

./manage.py lms --settings test test lms/djangoapps/open_ended_grading
"""

import json
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from mock import MagicMock, patch, Mock
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds

from xmodule import peer_grading_module
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.open_ended_grading_classes import peer_grading_service, controller_query_service
from xmodule.tests import test_util_open_ended

from courseware.tests import factories
from courseware.tests.helpers import LoginEnrollmentTestCase, check_for_get_code, check_for_post_code
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from lms.lib.xblock.runtime import LmsModuleSystem
from student.roles import CourseStaffRole
from edxmako.shortcuts import render_to_string
from student.models import unique_id_for_user

from open_ended_grading import staff_grading_service, views, utils

log = logging.getLogger(__name__)


class EmptyStaffGradingService(object):
    """
    A staff grading service that does not return a problem list from get_problem_list.
    Used for testing to see if error message for empty problem list is correctly displayed.
    """

    def get_problem_list(self, course_id, user_id):
        """
        Return a staff grading response that is missing a problem list key.
        """
        return json.dumps({'success': True, 'error': 'No problems found.'})


def make_instructor(course, user_email):
    """
    Makes a given user an instructor in a course.
    """
    CourseStaffRole(course.location).add_users(User.objects.get(email=user_email))


class StudentProblemListMockQuery(object):
    """
    Mock controller query service for testing student problem list functionality.
    """
    def get_grading_status_list(self, *args, **kwargs):
        """
        Get a mock grading status list with locations from the open_ended test course.
        @returns: json formatted grading status message.
        """
        grading_status_list = json.dumps(
            {
                "version": 1,
                "problem_list": [
                    {
                        "problem_name": "Test1",
                        "grader_type": "IN",
                        "eta_available": True,
                        "state": "Finished",
                        "eta": 259200,
                        "location": "i4x://edX/open_ended/combinedopenended/SampleQuestion1Attempt"
                    },
                    {
                        "problem_name": "Test2",
                        "grader_type": "NA",
                        "eta_available": True,
                        "state": "Waiting to be Graded",
                        "eta": 259200,
                        "location": "i4x://edX/open_ended/combinedopenended/SampleQuestion"
                    },
                    {
                        "problem_name": "Test3",
                        "grader_type": "PE",
                        "eta_available": True,
                        "state": "Waiting to be Graded",
                        "eta": 259200,
                        "location": "i4x://edX/open_ended/combinedopenended/SampleQuestion454"
                    },
                ],
                "success": True
            }
        )
        return grading_status_list


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestStaffGradingService(ModuleStoreTestCase, LoginEnrollmentTestCase):
    '''
    Check that staff grading service proxy works.  Basically just checking the
    access control and error handling logic -- all the actual work is on the
    backend.
    '''

    def setUp(self):
        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.location = 'TestLocation'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)

        self.course_id = "edX/toy/2012_Fall"
        self.toy = modulestore().get_course(self.course_id)

        make_instructor(self.toy, self.instructor)

        self.mock_service = staff_grading_service.staff_grading_service()

        self.logout()

    def test_access(self):
        """
        Make sure only staff have access.
        """
        self.login(self.student, self.password)

        # both get and post should return 404
        for view_name in ('staff_grading_get_next', 'staff_grading_save_grade'):
            url = reverse(view_name, kwargs={'course_id': self.course_id})
            check_for_get_code(self, 404, url)
            check_for_post_code(self, 404, url)

    def test_get_next(self):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_get_next', kwargs={'course_id': self.course_id})
        data = {'location': self.location}

        response = check_for_post_code(self, 200, url, data)

        content = json.loads(response.content)

        self.assertTrue(content['success'])
        self.assertEquals(content['submission_id'], self.mock_service.cnt)
        self.assertIsNotNone(content['submission'])
        self.assertIsNotNone(content['num_graded'])
        self.assertIsNotNone(content['min_for_ml'])
        self.assertIsNotNone(content['num_pending'])
        self.assertIsNotNone(content['prompt'])
        self.assertIsNotNone(content['ml_error_info'])
        self.assertIsNotNone(content['max_score'])
        self.assertIsNotNone(content['rubric'])

    def save_grade_base(self, skip=False):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_save_grade', kwargs={'course_id': self.course_id})

        data = {'score': '12',
                'feedback': 'great!',
                'submission_id': '123',
                'location': self.location,
                'submission_flagged': "true",
                'rubric_scores[]': ['1', '2']}
        if skip:
            data.update({'skipped': True})

        response = check_for_post_code(self, 200, url, data)
        content = json.loads(response.content)
        self.assertTrue(content['success'], str(content))
        self.assertEquals(content['submission_id'], self.mock_service.cnt)

    def test_save_grade(self):
        self.save_grade_base(skip=False)

    def test_save_grade_skip(self):
        self.save_grade_base(skip=True)

    def test_get_problem_list(self):
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_get_problem_list', kwargs={'course_id': self.course_id})
        data = {}

        response = check_for_post_code(self, 200, url, data)
        content = json.loads(response.content)

        self.assertTrue(content['success'])
        self.assertEqual(content['problem_list'], [])

    @patch('open_ended_grading.staff_grading_service._service', EmptyStaffGradingService())
    def test_get_problem_list_missing(self):
        """
        Test to see if a staff grading response missing a problem list is given the appropriate error.
        Mock the staff grading service to enable the key to be missing.
        """

        # Get a valid user object.
        instructor = User.objects.get(email=self.instructor)
        # Mock a request object.
        request = Mock(
            user=instructor,
        )
        # Get the response and load its content.
        response = json.loads(staff_grading_service.get_problem_list(request, self.course_id).content)

        # A valid response will have an "error" key.
        self.assertTrue('error' in response)
        # Check that the error text is correct.
        self.assertIn("Cannot find", response['error'])

    def test_save_grade_with_long_feedback(self):
        """
        Test if feedback is too long save_grade() should return error message.
        """
        self.login(self.instructor, self.password)

        url = reverse('staff_grading_save_grade', kwargs={'course_id': self.course_id})

        data = {
            'score': '12',
            'feedback': '',
            'submission_id': '123',
            'location': self.location,
            'submission_flagged': "false",
            'rubric_scores[]': ['1', '2']
        }

        feedback_fragment = "This is very long feedback."
        data["feedback"] = feedback_fragment * (
            (staff_grading_service.MAX_ALLOWED_FEEDBACK_LENGTH / len(feedback_fragment) + 1)
        )

        response = check_for_post_code(self, 200, url, data)
        content = json.loads(response.content)

        # Should not succeed.
        self.assertEquals(content['success'], False)
        self.assertEquals(
            content['error'],
            "Feedback is too long, Max length is {0} characters.".format(
                staff_grading_service.MAX_ALLOWED_FEEDBACK_LENGTH
            )
        )


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestPeerGradingService(ModuleStoreTestCase, LoginEnrollmentTestCase):
    '''
    Check that staff grading service proxy works.  Basically just checking the
    access control and error handling logic -- all the actual work is on the
    backend.
    '''

    def setUp(self):
        self.student = 'view@test.com'
        self.instructor = 'view2@test.com'
        self.password = 'foo'
        self.location = 'TestLocation'
        self.create_account('u1', self.student, self.password)
        self.create_account('u2', self.instructor, self.password)
        self.activate_user(self.student)
        self.activate_user(self.instructor)

        self.course_id = "edX/toy/2012_Fall"
        self.toy = modulestore().get_course(self.course_id)
        location = "i4x://edX/toy/peergrading/init"
        field_data = DictFieldData({'data': "<peergrading/>", 'location': location, 'category':'peergrading'})
        self.mock_service = peer_grading_service.MockPeerGradingService()
        self.system = LmsModuleSystem(
            static_url=settings.STATIC_URL,
            track_function=None,
            get_module=None,
            render_template=render_to_string,
            replace_urls=None,
            s3_interface=test_util_open_ended.S3_INTERFACE,
            open_ended_grading_interface=test_util_open_ended.OPEN_ENDED_GRADING_INTERFACE,
            mixins=settings.XBLOCK_MIXINS,
            error_descriptor_class=ErrorDescriptor,
        )
        self.descriptor = peer_grading_module.PeerGradingDescriptor(self.system, field_data, ScopeIds(None, None, None, None))
        self.descriptor.xmodule_runtime = self.system
        self.peer_module = self.descriptor
        self.peer_module.peer_gs = self.mock_service
        self.logout()

    def test_get_next_submission_success(self):
        data = {'location': self.location}

        response = self.peer_module.get_next_submission(data)
        content = response

        self.assertTrue(content['success'])
        self.assertIsNotNone(content['submission_id'])
        self.assertIsNotNone(content['prompt'])
        self.assertIsNotNone(content['submission_key'])
        self.assertIsNotNone(content['max_score'])

    def test_get_next_submission_missing_location(self):
        data = {}
        d = self.peer_module.get_next_submission(data)
        self.assertFalse(d['success'])
        self.assertEqual(d['error'], "Missing required keys: location")

    def test_save_grade_success(self):
        data = {
            'rubric_scores[]': [0, 0],
            'location': self.location,
            'submission_id': 1,
            'submission_key': 'fake key',
            'score': 2,
            'feedback': 'feedback',
            'submission_flagged': 'false',
            'answer_unknown': 'false',
            'rubric_scores_complete' : 'true'
        }

        qdict = MagicMock()

        def fake_get_item(key):
            return data[key]

        qdict.__getitem__.side_effect = fake_get_item
        qdict.getlist = fake_get_item
        qdict.keys = data.keys

        response = self.peer_module.save_grade(qdict)

        self.assertTrue(response['success'])

    def test_save_grade_missing_keys(self):
        data = {}
        d = self.peer_module.save_grade(data)
        self.assertFalse(d['success'])
        self.assertTrue(d['error'].find('Missing required keys:') > -1)

    def test_is_calibrated_success(self):
        data = {'location': self.location}
        response = self.peer_module.is_student_calibrated(data)

        self.assertTrue(response['success'])
        self.assertTrue('calibrated' in response)

    def test_is_calibrated_failure(self):
        data = {}
        response = self.peer_module.is_student_calibrated(data)
        self.assertFalse(response['success'])
        self.assertFalse('calibrated' in response)

    def test_show_calibration_essay_success(self):
        data = {'location': self.location}

        response = self.peer_module.show_calibration_essay(data)

        self.assertTrue(response['success'])
        self.assertIsNotNone(response['submission_id'])
        self.assertIsNotNone(response['prompt'])
        self.assertIsNotNone(response['submission_key'])
        self.assertIsNotNone(response['max_score'])

    def test_show_calibration_essay_missing_key(self):
        data = {}

        response = self.peer_module.show_calibration_essay(data)

        self.assertFalse(response['success'])
        self.assertEqual(response['error'], "Missing required keys: location")

    def test_save_calibration_essay_success(self):
        data = {
            'rubric_scores[]': [0, 0],
            'location': self.location,
            'submission_id': 1,
            'submission_key': 'fake key',
            'score': 2,
            'feedback': 'feedback',
            'submission_flagged': 'false'
        }

        qdict = MagicMock()

        def fake_get_item(key):
            return data[key]

        qdict.__getitem__.side_effect = fake_get_item
        qdict.getlist = fake_get_item
        qdict.keys = data.keys

        response = self.peer_module.save_calibration_essay(qdict)
        self.assertTrue(response['success'])
        self.assertTrue('actual_score' in response)

    def test_save_calibration_essay_missing_keys(self):
        data = {}
        response = self.peer_module.save_calibration_essay(data)
        self.assertFalse(response['success'])
        self.assertTrue(response['error'].find('Missing required keys:') > -1)
        self.assertFalse('actual_score' in response)

    def test_save_grade_with_long_feedback(self):
        """
        Test if feedback is too long save_grade() should return error message.
        """
        data = {
            'rubric_scores[]': [0, 0],
            'location': self.location,
            'submission_id': 1,
            'submission_key': 'fake key',
            'score': 2,
            'feedback': '',
            'submission_flagged': 'false',
            'answer_unknown': 'false',
            'rubric_scores_complete': 'true'
        }

        feedback_fragment = "This is very long feedback."
        data["feedback"] = feedback_fragment * (
            (staff_grading_service.MAX_ALLOWED_FEEDBACK_LENGTH / len(feedback_fragment) + 1)
        )

        response_dict = self.peer_module.save_grade(data)

        # Should not succeed.
        self.assertEquals(response_dict['success'], False)
        self.assertEquals(
            response_dict['error'],
            "Feedback is too long, Max length is {0} characters.".format(
                staff_grading_service.MAX_ALLOWED_FEEDBACK_LENGTH
            )
        )


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestPanel(ModuleStoreTestCase):
    """
    Run tests on the open ended panel
    """

    def setUp(self):
        # Toy courses should be loaded
        self.course_name = 'edX/open_ended/2012_Fall'
        self.course = modulestore().get_course(self.course_name)
        self.user = factories.UserFactory()

    def test_open_ended_panel(self):
        """
        Test to see if the peer grading module in the demo course is found
        @return:
        """
        found_module, peer_grading_module = views.find_peer_grading_module(self.course)
        self.assertTrue(found_module)

    @patch(
        'open_ended_grading.utils.create_controller_query_service',
        Mock(
            return_value=controller_query_service.MockControllerQueryService(
                settings.OPEN_ENDED_GRADING_INTERFACE,
                utils.SYSTEM
            )
        )
    )
    def test_problem_list(self):
        """
        Ensure that the problem list from the grading controller server can be rendered properly locally
        @return:
        """
        request = Mock(user=self.user)
        response = views.student_problem_list(request, self.course.id)
        self.assertRegexpMatches(response.content, "Here is a list of open ended problems for this course.")


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestPeerGradingFound(ModuleStoreTestCase):
    """
    Test to see if peer grading modules can be found properly.
    """

    def setUp(self):
        self.course_name = 'edX/open_ended_nopath/2012_Fall'
        self.course = modulestore().get_course(self.course_name)

    def test_peer_grading_nopath(self):
        """
        The open_ended_nopath course contains a peer grading module with no path to it.
        Ensure that the exception is caught.
        """

        found, url = views.find_peer_grading_module(self.course)
        self.assertEqual(found, False)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestStudentProblemList(ModuleStoreTestCase):
    """
    Test if the student problem list correctly fetches and parses problems.
    """

    def setUp(self):
        # Load an open ended course with several problems.
        self.course_name = 'edX/open_ended/2012_Fall'
        self.course = modulestore().get_course(self.course_name)
        self.user = factories.UserFactory()
        # Enroll our user in our course and make them an instructor.
        make_instructor(self.course, self.user.email)

    @patch(
        'open_ended_grading.utils.create_controller_query_service',
        Mock(return_value=StudentProblemListMockQuery())
    )
    def test_get_problem_list(self):
        """
        Test to see if the StudentProblemList class can get and parse a problem list from ORA.
        Mock the get_grading_status_list function using StudentProblemListMockQuery.
        """
        # Initialize a StudentProblemList object.
        student_problem_list = utils.StudentProblemList(self.course.id, unique_id_for_user(self.user))
        # Get the initial problem list from ORA.
        success = student_problem_list.fetch_from_grading_service()
        # Should be successful, and we should have three problems.  See mock class for details.
        self.assertTrue(success)
        self.assertEqual(len(student_problem_list.problem_list), 3)

        # See if the problem locations are valid.
        valid_problems = student_problem_list.add_problem_data(reverse('courses'))
        # One location is invalid, so we should now have two.
        self.assertEqual(len(valid_problems), 2)
        # Ensure that human names are being set properly.
        self.assertEqual(valid_problems[0]['grader_type_display_name'], "Instructor Assessment")
