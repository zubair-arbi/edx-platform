"""Test the openended_post management command."""

from datetime import datetime
import json
from mock import patch, ANY
from pytz import UTC

from django.test.utils import override_settings

import capa.xqueue_interface as xqueue_interface
from xmodule.modulestore import Location
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.open_ended_grading_classes.openendedchild import OpenEndedChild
from xmodule.tests.test_util_open_ended import (
    STATE_INITIAL, STATE_ACCESSING, STATE_POST_ASSESSMENT
)

from courseware.courses import get_course_with_access
from courseware.tests.factories import StudentModuleFactory, UserFactory
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from student.models import anonymous_id_for_user

from instructor.management.commands.openended_post import post_submission_for_student
from instructor.management.commands.openended_stats import calculate_task_statistics
from instructor.utils import get_module_for_student


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class OpenEndedPostTest(ModuleStoreTestCase):
    """Test the openended_post management command."""

    def setUp(self):
        self.course_id = "edX/open_ended/2012_Fall"
        self.problem_location = Location(["i4x", "edX", "open_ended", "combinedopenended", "SampleQuestion"])
        self.self_assessment_task_number = 0
        self.open_ended_task_number = 1

        self.student_on_initial = UserFactory()
        self.student_on_accessing = UserFactory()
        self.student_on_post_assessment = UserFactory()

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_initial,
            grade=0,
            max_grade=1,
            state=STATE_INITIAL
        )

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_accessing,
            grade=0,
            max_grade=1,
            state=STATE_ACCESSING
        )

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_post_assessment,
            grade=0,
            max_grade=1,
            state=STATE_POST_ASSESSMENT
        )

    def test_post_submission_for_student_on_initial(self):
        course = get_course_with_access(self.student_on_initial, self.course_id, 'load')

        dry_run_result = post_submission_for_student(self.student_on_initial, course, self.problem_location, self.open_ended_task_number, dry_run=True)
        self.assertFalse(dry_run_result)

        result = post_submission_for_student(self.student_on_initial, course, self.problem_location, self.open_ended_task_number, dry_run=False)
        self.assertFalse(result)

    def test_post_submission_for_student_on_accessing(self):
        course = get_course_with_access(self.student_on_accessing, self.course_id, 'load')

        dry_run_result = post_submission_for_student(self.student_on_accessing, course, self.problem_location, self.open_ended_task_number, dry_run=True)
        self.assertFalse(dry_run_result)

        with patch('capa.xqueue_interface.XQueueInterface.send_to_queue') as mock_send_to_queue:
            mock_send_to_queue.return_value = (0, "Successfully queued")

            module = get_module_for_student(self.student_on_accessing, course, self.problem_location)
            task = module.child_module.get_task_number(self.open_ended_task_number)

            student_response = "Here is an answer."
            student_anonymous_id = anonymous_id_for_user(self.student_on_accessing, '')
            submission_time = datetime.strftime(datetime.now(UTC), xqueue_interface.dateformat)

            result = post_submission_for_student(self.student_on_accessing, course, self.problem_location, self.open_ended_task_number, dry_run=False)

            self.assertTrue(result)
            mock_send_to_queue_body_arg = json.loads(mock_send_to_queue.call_args[1]['body'])
            self.assertEqual(mock_send_to_queue_body_arg['max_score'], 2)
            self.assertEqual(mock_send_to_queue_body_arg['student_response'], student_response)
            body_arg_student_info = json.loads(mock_send_to_queue_body_arg['student_info'])
            self.assertEqual(body_arg_student_info['anonymous_student_id'], student_anonymous_id)
            self.assertGreaterEqual(body_arg_student_info['submission_time'], submission_time)

    def test_post_submission_for_student_on_post_assessment(self):
        course = get_course_with_access(self.student_on_post_assessment, self.course_id, 'load')

        dry_run_result = post_submission_for_student(self.student_on_post_assessment, course, self.problem_location, self.open_ended_task_number, dry_run=True)
        self.assertFalse(dry_run_result)

        result = post_submission_for_student(self.student_on_post_assessment, course, self.problem_location, self.open_ended_task_number, dry_run=False)
        self.assertFalse(result)

    def test_post_submission_for_student_invalid_task(self):
        course = get_course_with_access(self.student_on_accessing, self.course_id, 'load')

        result = post_submission_for_student(self.student_on_accessing, course, self.problem_location, self.self_assessment_task_number, dry_run=False)
        self.assertFalse(result)

        out_of_bounds_task_number = 3
        result = post_submission_for_student(self.student_on_accessing, course, self.problem_location, out_of_bounds_task_number, dry_run=False)
        self.assertFalse(result)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class OpenEndedStatsTest(ModuleStoreTestCase):
    """Test the openended_stats management command."""

    def setUp(self):
        self.course_id = "edX/open_ended/2012_Fall"
        self.problem_location = Location(["i4x", "edX", "open_ended", "combinedopenended", "SampleQuestion"])
        self.task_number = 1
        self.invalid_task_number = 3

        self.student_on_initial = UserFactory()
        self.student_on_accessing = UserFactory()
        self.student_on_post_assessment = UserFactory()

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_initial,
            grade=0,
            max_grade=1,
            state=STATE_INITIAL
        )

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_accessing,
            grade=0,
            max_grade=1,
            state=STATE_ACCESSING
        )

        StudentModuleFactory.create(
            course_id=self.course_id,
            module_state_key=self.problem_location,
            student=self.student_on_post_assessment,
            grade=0,
            max_grade=1,
            state=STATE_POST_ASSESSMENT
        )

        self.students = [self.student_on_initial, self.student_on_accessing, self.student_on_post_assessment]

    def test_calculate_task_statistics(self):
        course = get_course_with_access(self.student_on_accessing, self.course_id, 'load')
        stats = calculate_task_statistics(self.students, course, self.problem_location, self.task_number, write_to_file=False)
        self.assertEqual(stats[OpenEndedChild.INITIAL], 1)
        self.assertEqual(stats[OpenEndedChild.ASSESSING], 1)
        self.assertEqual(stats[OpenEndedChild.POST_ASSESSMENT], 1)
        self.assertEqual(stats[OpenEndedChild.DONE], 0)

        stats = calculate_task_statistics(self.students, course, self.problem_location, self.invalid_task_number, write_to_file=False)
        self.assertEqual(stats[OpenEndedChild.INITIAL], 0)
        self.assertEqual(stats[OpenEndedChild.ASSESSING], 0)
        self.assertEqual(stats[OpenEndedChild.POST_ASSESSMENT], 0)
        self.assertEqual(stats[OpenEndedChild.DONE], 0)
