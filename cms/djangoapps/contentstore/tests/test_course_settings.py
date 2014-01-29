"""
Tests for Studio Course Settings.
"""
import datetime
import json
import copy
import mock

from django.utils.timezone import UTC
from django.test.utils import override_settings

from models.settings.course_details import (CourseDetails, CourseSettingsEncoder)
from models.settings.course_grading import CourseGradingModel
from contentstore.utils import get_modulestore, EXTRA_TAB_PANELS
from xmodule.modulestore.tests.factories import CourseFactory


from models.settings.course_metadata import CourseMetadata
from xmodule.fields import Date

from .utils import CourseTestCase
from xmodule.modulestore.django import loc_mapper, modulestore
from contentstore.views.component import ADVANCED_COMPONENT_POLICY_KEY


class CourseDetailsTestCase(CourseTestCase):
    """
    Tests the first course settings page (course dates, overview, etc.).
    """
    def test_virgin_fetch(self):
        details = CourseDetails.fetch(self.course_locator)
        self.assertEqual(details.org, self.course.location.org, "Org not copied into")
        self.assertEqual(details.course_id, self.course.location.course, "Course_id not copied into")
        self.assertEqual(details.run, self.course.location.name, "Course name not copied into")
        self.assertEqual(details.course_image_name, self.course.course_image)
        self.assertIsNotNone(details.start_date.tzinfo)
        self.assertIsNone(details.end_date, "end date somehow initialized " + str(details.end_date))
        self.assertIsNone(details.enrollment_start, "enrollment_start date somehow initialized " + str(details.enrollment_start))
        self.assertIsNone(details.enrollment_end, "enrollment_end date somehow initialized " + str(details.enrollment_end))
        self.assertIsNone(details.syllabus, "syllabus somehow initialized" + str(details.syllabus))
        self.assertIsNone(details.intro_video, "intro_video somehow initialized" + str(details.intro_video))
        self.assertIsNone(details.effort, "effort somehow initialized" + str(details.effort))

    def test_encoder(self):
        details = CourseDetails.fetch(self.course_locator)
        jsondetails = json.dumps(details, cls=CourseSettingsEncoder)
        jsondetails = json.loads(jsondetails)
        self.assertEqual(jsondetails['course_image_name'], self.course.course_image)
        self.assertIsNone(jsondetails['end_date'], "end date somehow initialized ")
        self.assertIsNone(jsondetails['enrollment_start'], "enrollment_start date somehow initialized ")
        self.assertIsNone(jsondetails['enrollment_end'], "enrollment_end date somehow initialized ")
        self.assertIsNone(jsondetails['syllabus'], "syllabus somehow initialized")
        self.assertIsNone(jsondetails['intro_video'], "intro_video somehow initialized")
        self.assertIsNone(jsondetails['effort'], "effort somehow initialized")

    def test_ooc_encoder(self):
        """
        Test the encoder out of its original constrained purpose to see if it functions for general use
        """
        details = {
            'number': 1,
            'string': 'string',
            'datetime': datetime.datetime.now(UTC())
        }
        jsondetails = json.dumps(details, cls=CourseSettingsEncoder)
        jsondetails = json.loads(jsondetails)

        self.assertEquals(1, jsondetails['number'])
        self.assertEqual(jsondetails['string'], 'string')

    def test_update_and_fetch(self):
        jsondetails = CourseDetails.fetch(self.course_locator)
        jsondetails.syllabus = "<a href='foo'>bar</a>"
        # encode - decode to convert date fields and other data which changes form
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).syllabus,
            jsondetails.syllabus, "After set syllabus"
        )
        jsondetails.overview = "Overview"
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).overview,
            jsondetails.overview, "After set overview"
        )
        jsondetails.intro_video = "intro_video"
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).intro_video,
            jsondetails.intro_video, "After set intro_video"
        )
        jsondetails.effort = "effort"
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).effort,
            jsondetails.effort, "After set effort"
        )
        jsondetails.start_date = datetime.datetime(2010, 10, 1, 0, tzinfo=UTC())
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).start_date,
            jsondetails.start_date
        )
        jsondetails.course_image_name = "an_image.jpg"
        self.assertEqual(
            CourseDetails.update_from_json(self.course_locator, jsondetails.__dict__).course_image_name,
            jsondetails.course_image_name
        )

    @override_settings(MKTG_URLS={'ROOT': 'dummy-root'})
    def test_marketing_site_fetch(self):
        settings_details_url = self.course_locator.url_reverse('settings/details/')

        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': True}):
            response = self.client.get_html(settings_details_url)
            self.assertNotContains(response, "Course Summary Page")
            self.assertNotContains(response, "Send a note to students via email")
            self.assertContains(response, "course summary page will not be viewable")

            self.assertContains(response, "Course Start Date")
            self.assertContains(response, "Course End Date")
            self.assertContains(response, "Enrollment Start Date")
            self.assertContains(response, "Enrollment End Date")
            self.assertContains(response, "not the dates shown on your course summary page")

            self.assertContains(response, "Introducing Your Course")
            self.assertContains(response, "Course Image")
            self.assertNotContains(response,"Course Overview")
            self.assertNotContains(response,"Course Introduction Video")
            self.assertNotContains(response, "Requirements")

    def test_regular_site_fetch(self):
        settings_details_url = self.course_locator.url_reverse('settings/details/')

        with mock.patch.dict('django.conf.settings.FEATURES', {'ENABLE_MKTG_SITE': False}):
            response = self.client.get_html(settings_details_url)
            self.assertContains(response, "Course Summary Page")
            self.assertContains(response, "Send a note to students via email")
            self.assertNotContains(response, "course summary page will not be viewable")

            self.assertContains(response, "Course Start Date")
            self.assertContains(response, "Course End Date")
            self.assertContains(response, "Enrollment Start Date")
            self.assertContains(response, "Enrollment End Date")
            self.assertNotContains(response, "not the dates shown on your course summary page")

            self.assertContains(response, "Introducing Your Course")
            self.assertContains(response, "Course Image")
            self.assertContains(response,"Course Overview")
            self.assertContains(response,"Course Introduction Video")
            self.assertContains(response, "Requirements")


class CourseDetailsViewTest(CourseTestCase):
    """
    Tests for modifying content on the first course settings page (course dates, overview, etc.).
    """
    def alter_field(self, url, details, field, val):
        """
        Change the one field to the given value and then invoke the update post to see if it worked.
        """
        setattr(details, field, val)
        # Need to partially serialize payload b/c the mock doesn't handle it correctly
        payload = copy.copy(details.__dict__)
        payload['start_date'] = CourseDetailsViewTest.convert_datetime_to_iso(details.start_date)
        payload['end_date'] = CourseDetailsViewTest.convert_datetime_to_iso(details.end_date)
        payload['enrollment_start'] = CourseDetailsViewTest.convert_datetime_to_iso(details.enrollment_start)
        payload['enrollment_end'] = CourseDetailsViewTest.convert_datetime_to_iso(details.enrollment_end)
        resp = self.client.ajax_post(url, payload)
        self.compare_details_with_encoding(json.loads(resp.content), details.__dict__, field + str(val))

    @staticmethod
    def convert_datetime_to_iso(datetime_obj):
        """
        Use the xblock serializer to convert the datetime
        """
        return Date().to_json(datetime_obj)

    def test_update_and_fetch(self):
        details = CourseDetails.fetch(self.course_locator)

        # resp s/b json from here on
        url = self.course_locator.url_reverse('settings/details/')
        resp = self.client.get_json(url)
        self.compare_details_with_encoding(json.loads(resp.content), details.__dict__, "virgin get")

        utc = UTC()
        self.alter_field(url, details, 'start_date', datetime.datetime(2012, 11, 12, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'start_date', datetime.datetime(2012, 11, 1, 13, 30, tzinfo=utc))
        self.alter_field(url, details, 'end_date', datetime.datetime(2013, 2, 12, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'enrollment_start', datetime.datetime(2012, 10, 12, 1, 30, tzinfo=utc))

        self.alter_field(url, details, 'enrollment_end', datetime.datetime(2012, 11, 15, 1, 30, tzinfo=utc))
        self.alter_field(url, details, 'overview', "Overview")
        self.alter_field(url, details, 'intro_video', "intro_video")
        self.alter_field(url, details, 'effort', "effort")
        self.alter_field(url, details, 'course_image_name', "course_image_name")

    def compare_details_with_encoding(self, encoded, details, context):
        """
        compare all of the fields of the before and after dicts
        """
        self.compare_date_fields(details, encoded, context, 'start_date')
        self.compare_date_fields(details, encoded, context, 'end_date')
        self.compare_date_fields(details, encoded, context, 'enrollment_start')
        self.compare_date_fields(details, encoded, context, 'enrollment_end')
        self.assertEqual(details['overview'], encoded['overview'], context + " overviews not ==")
        self.assertEqual(details['intro_video'], encoded.get('intro_video', None), context + " intro_video not ==")
        self.assertEqual(details['effort'], encoded['effort'], context + " efforts not ==")
        self.assertEqual(details['course_image_name'], encoded['course_image_name'], context + " images not ==")

    def compare_date_fields(self, details, encoded, context, field):
        """
        Compare the given date fields between the before and after doing json deserialization
        """
        if details[field] is not None:
            date = Date()
            if field in encoded and encoded[field] is not None:
                dt1 = date.from_json(encoded[field])
                dt2 = details[field]

                self.assertEqual(dt1, dt2, msg="{} != {} at {}".format(dt1, dt2, context))
            else:
                self.fail(field + " missing from encoded but in details at " + context)
        elif field in encoded and encoded[field] is not None:
            self.fail(field + " included in encoding but missing from details at " + context)


class CourseGradingTest(CourseTestCase):
    """
    Tests for the course settings grading page.
    """
    def test_initial_grader(self):
        test_grader = CourseGradingModel(self.course)
        self.assertIsNotNone(test_grader.graders)
        self.assertIsNotNone(test_grader.grade_cutoffs)

    def test_fetch_grader(self):
        test_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertIsNotNone(test_grader.graders, "No graders")
        self.assertIsNotNone(test_grader.grade_cutoffs, "No cutoffs")

        for i, grader in enumerate(test_grader.graders):
            subgrader = CourseGradingModel.fetch_grader(self.course_locator, i)
            self.assertDictEqual(grader, subgrader, str(i) + "th graders not equal")

    def test_update_from_json(self):
        test_grader = CourseGradingModel.fetch(self.course_locator)
        altered_grader = CourseGradingModel.update_from_json(self.course_locator, test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "Noop update")

        test_grader.graders[0]['weight'] = test_grader.graders[0].get('weight') * 2
        altered_grader = CourseGradingModel.update_from_json(self.course_locator, test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "Weight[0] * 2")

        test_grader.grade_cutoffs['D'] = 0.3
        altered_grader = CourseGradingModel.update_from_json(self.course_locator, test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "cutoff add D")

        test_grader.grace_period = {'hours': 4, 'minutes': 5, 'seconds': 0}
        altered_grader = CourseGradingModel.update_from_json(self.course_locator, test_grader.__dict__)
        self.assertDictEqual(test_grader.__dict__, altered_grader.__dict__, "4 hour grace period")

    def test_update_grader_from_json(self):
        test_grader = CourseGradingModel.fetch(self.course_locator)
        altered_grader = CourseGradingModel.update_grader_from_json(self.course_locator, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "Noop update")

        test_grader.graders[1]['min_count'] = test_grader.graders[1].get('min_count') + 2
        altered_grader = CourseGradingModel.update_grader_from_json(self.course_locator, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "min_count[1] + 2")

        test_grader.graders[1]['drop_count'] = test_grader.graders[1].get('drop_count') + 1
        altered_grader = CourseGradingModel.update_grader_from_json(self.course_locator, test_grader.graders[1])
        self.assertDictEqual(test_grader.graders[1], altered_grader, "drop_count[1] + 2")

    def test_update_cutoffs_from_json(self):
        test_grader = CourseGradingModel.fetch(self.course_locator)
        CourseGradingModel.update_cutoffs_from_json(self.course_locator, test_grader.grade_cutoffs)
        # Unlike other tests, need to actually perform a db fetch for this test since update_cutoffs_from_json
        #  simply returns the cutoffs you send into it, rather than returning the db contents.
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertDictEqual(test_grader.grade_cutoffs, altered_grader.grade_cutoffs, "Noop update")

        test_grader.grade_cutoffs['D'] = 0.3
        CourseGradingModel.update_cutoffs_from_json(self.course_locator, test_grader.grade_cutoffs)
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertDictEqual(test_grader.grade_cutoffs, altered_grader.grade_cutoffs, "cutoff add D")

        test_grader.grade_cutoffs['Pass'] = 0.75
        CourseGradingModel.update_cutoffs_from_json(self.course_locator, test_grader.grade_cutoffs)
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertDictEqual(test_grader.grade_cutoffs, altered_grader.grade_cutoffs, "cutoff change 'Pass'")

    def test_delete_grace_period(self):
        test_grader = CourseGradingModel.fetch(self.course_locator)
        CourseGradingModel.update_grace_period_from_json(self.course_locator, test_grader.grace_period)
        # update_grace_period_from_json doesn't return anything, so query the db for its contents.
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertEqual(test_grader.grace_period, altered_grader.grace_period, "Noop update")

        test_grader.grace_period = {'hours': 15, 'minutes': 5, 'seconds': 30}
        CourseGradingModel.update_grace_period_from_json(self.course_locator, test_grader.grace_period)
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        self.assertDictEqual(test_grader.grace_period, altered_grader.grace_period, "Adding in a grace period")

        test_grader.grace_period = {'hours': 1, 'minutes': 10, 'seconds': 0}
        # Now delete the grace period
        CourseGradingModel.delete_grace_period(self.course_locator)
        # update_grace_period_from_json doesn't return anything, so query the db for its contents.
        altered_grader = CourseGradingModel.fetch(self.course_locator)
        # Once deleted, the grace period should simply be None
        self.assertEqual(None, altered_grader.grace_period, "Delete grace period")

    def test_update_section_grader_type(self):
        # Get the descriptor and the section_grader_type and assert they are the default values
        descriptor = get_modulestore(self.course.location).get_item(self.course.location)
        section_grader_type = CourseGradingModel.get_section_grader_type(self.course_locator)

        self.assertEqual('notgraded', section_grader_type['graderType'])
        self.assertEqual(None, descriptor.format)
        self.assertEqual(False, descriptor.graded)

        # Change the default grader type to Homework, which should also mark the section as graded
        CourseGradingModel.update_section_grader_type(self.course, 'Homework')
        descriptor = get_modulestore(self.course.location).get_item(self.course.location)
        section_grader_type = CourseGradingModel.get_section_grader_type(self.course_locator)

        self.assertEqual('Homework', section_grader_type['graderType'])
        self.assertEqual('Homework', descriptor.format)
        self.assertEqual(True, descriptor.graded)

        # Change the grader type back to notgraded, which should also unmark the section as graded
        CourseGradingModel.update_section_grader_type(self.course, 'notgraded')
        descriptor = get_modulestore(self.course.location).get_item(self.course.location)
        section_grader_type = CourseGradingModel.get_section_grader_type(self.course_locator)

        self.assertEqual('notgraded', section_grader_type['graderType'])
        self.assertEqual(None, descriptor.format)
        self.assertEqual(False, descriptor.graded)

    def test_get_set_grader_types_ajax(self):
        """
        Test configuring the graders via ajax calls
        """
        grader_type_url_base = self.course_locator.url_reverse('settings/grading')
        # test get whole
        response = self.client.get_json(grader_type_url_base)
        whole_model = json.loads(response.content)
        self.assertIn('graders', whole_model)
        self.assertIn('grade_cutoffs', whole_model)
        self.assertIn('grace_period', whole_model)
        # test post/update whole
        whole_model['grace_period'] = {'hours': 1, 'minutes': 30, 'seconds': 0}
        response = self.client.ajax_post(grader_type_url_base, whole_model)
        self.assertEqual(200, response.status_code)
        response = self.client.get_json(grader_type_url_base)
        whole_model = json.loads(response.content)
        self.assertEqual(whole_model['grace_period'], {'hours': 1, 'minutes': 30, 'seconds': 0})
        # test get one grader
        self.assertGreater(len(whole_model['graders']), 1)  # ensure test will make sense
        response = self.client.get_json(grader_type_url_base + '/1')
        grader_sample = json.loads(response.content)
        self.assertEqual(grader_sample, whole_model['graders'][1])
        # test add grader
        new_grader = {
            "type": "Extra Credit",
            "min_count": 1,
            "drop_count": 2,
            "short_label": None,
            "weight": 15,
        }
        response = self.client.ajax_post(
            '{}/{}'.format(grader_type_url_base, len(whole_model['graders'])),
            new_grader
        )
        self.assertEqual(200, response.status_code)
        grader_sample = json.loads(response.content)
        new_grader['id'] = len(whole_model['graders'])
        self.assertEqual(new_grader, grader_sample)
        # test delete grader
        response = self.client.delete(grader_type_url_base + '/1', HTTP_ACCEPT="application/json")
        self.assertEqual(204, response.status_code)
        response = self.client.get_json(grader_type_url_base)
        updated_model = json.loads(response.content)
        new_grader['id'] -= 1  # one fewer and the id mutates
        self.assertIn(new_grader, updated_model['graders'])
        self.assertNotIn(whole_model['graders'][1], updated_model['graders'])

    def setup_test_set_get_section_grader_ajax(self):
        """
        Populate the course, grab a section, get the url for the assignment type access
        """
        self.populateCourse()
        sections = get_modulestore(self.course_location).get_items(
            self.course_location.replace(category="sequential", name=None)
        )
        # see if test makes sense
        self.assertGreater(len(sections), 0, "No sections found")
        section = sections[0]  # just take the first one
        section_locator = loc_mapper().translate_location(self.course_location.course_id, section.location, False, True)
        return section_locator.url_reverse('xblock')

    def test_set_get_section_grader_ajax(self):
        """
        Test setting and getting section grades via the grade as url
        """
        grade_type_url = self.setup_test_set_get_section_grader_ajax()
        response = self.client.ajax_post(grade_type_url, {'graderType': u'Homework'})
        self.assertEqual(200, response.status_code)
        response = self.client.get_json(grade_type_url + '?fields=graderType')
        self.assertEqual(json.loads(response.content).get('graderType'), u'Homework')
        # and unset
        response = self.client.ajax_post(grade_type_url, {'graderType': u'notgraded'})
        self.assertEqual(200, response.status_code)
        response = self.client.get_json(grade_type_url + '?fields=graderType')
        self.assertEqual(json.loads(response.content).get('graderType'), u'notgraded')


class CourseMetadataEditingTest(CourseTestCase):
    """
    Tests for CourseMetadata.
    """
    def setUp(self):
        CourseTestCase.setUp(self)
        self.fullcourse = CourseFactory.create(org='edX', course='999', display_name='Robot Super Course')
        self.course_setting_url = self.course_locator.url_reverse('settings/advanced')
        self.fullcourse_setting_url = loc_mapper().translate_location(
            self.fullcourse.location.course_id,
            self.fullcourse.location, False, True
        ).url_reverse('settings/advanced')

    def test_fetch_initial_fields(self):
        test_model = CourseMetadata.fetch(self.course)
        self.assertIn('display_name', test_model, 'Missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")

        test_model = CourseMetadata.fetch(self.fullcourse)
        self.assertNotIn('graceperiod', test_model, 'blacklisted field leaked in')
        self.assertIn('display_name', test_model, 'full missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")
        self.assertIn('rerandomize', test_model, 'Missing rerandomize metadata field')
        self.assertIn('showanswer', test_model, 'showanswer field ')
        self.assertIn('xqa_key', test_model, 'xqa_key field ')

    def test_update_from_json(self):
        test_model = CourseMetadata.update_from_json(self.course, {
            "advertised_start": "start A",
            "days_early_for_beta": 2
        })
        self.update_check(test_model)
        # try fresh fetch to ensure persistence
        fresh = modulestore().get_item(self.course_location)
        test_model = CourseMetadata.fetch(fresh)
        self.update_check(test_model)
        # now change some of the existing metadata
        test_model = CourseMetadata.update_from_json(fresh, {
            "advertised_start": "start B",
            "display_name": "jolly roger"}
        )
        self.assertIn('display_name', test_model, 'Missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'jolly roger', "not expected value")
        self.assertIn('advertised_start', test_model, 'Missing revised advertised_start metadata field')
        self.assertEqual(test_model['advertised_start'], 'start B', "advertised_start not expected value")

    def update_check(self, test_model):
        self.assertIn('display_name', test_model, 'Missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")
        self.assertIn('advertised_start', test_model, 'Missing new advertised_start metadata field')
        self.assertEqual(test_model['advertised_start'], 'start A', "advertised_start not expected value")
        self.assertIn('days_early_for_beta', test_model, 'Missing days_early_for_beta metadata field')
        self.assertEqual(test_model['days_early_for_beta'], 2, "days_early_for_beta not expected value")

    def test_delete_key(self):
        test_model = CourseMetadata.update_from_json(
            self.fullcourse, {
                "unsetKeys": ['showanswer', 'xqa_key']
            }
        )
        # ensure no harm
        self.assertNotIn('graceperiod', test_model, 'blacklisted field leaked in')
        self.assertIn('display_name', test_model, 'full missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")
        self.assertIn('rerandomize', test_model, 'Missing rerandomize metadata field')
        # check for deletion effectiveness
        self.assertEqual('finished', test_model['showanswer'], 'showanswer field still in')
        self.assertEqual(None, test_model['xqa_key'], 'xqa_key field still in')

    def test_http_fetch_initial_fields(self):
        response = self.client.get_json(self.course_setting_url)
        test_model = json.loads(response.content)
        self.assertIn('display_name', test_model, 'Missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")

        response = self.client.get_json(self.fullcourse_setting_url)
        test_model = json.loads(response.content)
        self.assertNotIn('graceperiod', test_model, 'blacklisted field leaked in')
        self.assertIn('display_name', test_model, 'full missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'Robot Super Course', "not expected value")
        self.assertIn('rerandomize', test_model, 'Missing rerandomize metadata field')
        self.assertIn('showanswer', test_model, 'showanswer field ')
        self.assertIn('xqa_key', test_model, 'xqa_key field ')

    def test_http_update_from_json(self):
        response = self.client.ajax_post(self.course_setting_url, {
            "advertised_start": "start A",
            "testcenter_info": {"c": "test"},
            "days_early_for_beta": 2,
            "unsetKeys": ['showanswer', 'xqa_key'],
        })
        test_model = json.loads(response.content)
        self.update_check(test_model)
        self.assertEqual('finished', test_model['showanswer'], 'showanswer field still in')
        self.assertEqual(None, test_model['xqa_key'], 'xqa_key field still in')

        response = self.client.get_json(self.course_setting_url)
        test_model = json.loads(response.content)
        self.update_check(test_model)
        # now change some of the existing metadata
        response = self.client.ajax_post(self.course_setting_url, {
            "advertised_start": "start B",
            "display_name": "jolly roger"
        })
        test_model = json.loads(response.content)
        self.assertIn('display_name', test_model, 'Missing editable metadata field')
        self.assertEqual(test_model['display_name'], 'jolly roger', "not expected value")
        self.assertIn('advertised_start', test_model, 'Missing revised advertised_start metadata field')
        self.assertEqual(test_model['advertised_start'], 'start B', "advertised_start not expected value")

    def test_advanced_components_munge_tabs(self):
        """
        Test that adding and removing specific advanced components adds and removes tabs.
        """
        self.assertNotIn(EXTRA_TAB_PANELS.get("open_ended"), self.course.tabs)
        self.assertNotIn(EXTRA_TAB_PANELS.get("notes"), self.course.tabs)
        self.client.ajax_post(self.course_setting_url, {
            ADVANCED_COMPONENT_POLICY_KEY: ["combinedopenended"]
        })
        course = modulestore().get_item(self.course_location)
        self.assertIn(EXTRA_TAB_PANELS.get("open_ended"), course.tabs)
        self.assertNotIn(EXTRA_TAB_PANELS.get("notes"), course.tabs)
        self.client.ajax_post(self.course_setting_url, {
            ADVANCED_COMPONENT_POLICY_KEY: []
        })
        course = modulestore().get_item(self.course_location)
        self.assertNotIn(EXTRA_TAB_PANELS.get("open_ended"), course.tabs)


class CourseGraderUpdatesTest(CourseTestCase):
    """
    Test getting, deleting, adding, & updating graders
    """
    def setUp(self):
        """Compute the url to use in tests"""
        super(CourseGraderUpdatesTest, self).setUp()
        self.url = self.course_locator.url_reverse('settings/grading')
        self.starting_graders = CourseGradingModel(self.course).graders

    def test_get(self):
        """Test getting a specific grading type record."""
        resp = self.client.get_json(self.url + '/0')
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(self.starting_graders[0], obj)

    def test_delete(self):
        """Test deleting a specific grading type record."""
        resp = self.client.delete(self.url + '/0', HTTP_ACCEPT="application/json")
        self.assertEqual(resp.status_code, 204)
        current_graders = CourseGradingModel.fetch(self.course_locator).graders
        self.assertNotIn(self.starting_graders[0], current_graders)
        self.assertEqual(len(self.starting_graders) - 1, len(current_graders))

    def test_update(self):
        """Test updating a specific grading type record."""
        grader = {
            "id": 0,
            "type": "manual",
            "min_count": 5,
            "drop_count": 10,
            "short_label": "yo momma",
            "weight": 17.3,
        }
        resp = self.client.ajax_post(self.url + '/0', grader)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj, grader)
        current_graders = CourseGradingModel.fetch(self.course_locator).graders
        self.assertEqual(len(self.starting_graders), len(current_graders))

    def test_add(self):
        """Test adding a grading type record."""
        # the same url works for changing the whole grading model (graceperiod, cutoffs, and grading types) when
        # the grading_index is None; thus, using None to imply adding a grading_type doesn't work; so, it uses an
        # index out of bounds to imply create item.
        grader = {
            "type": "manual",
            "min_count": 5,
            "drop_count": 10,
            "short_label": "yo momma",
            "weight": 17.3,
        }
        resp = self.client.ajax_post('{}/{}'.format(self.url, len(self.starting_graders) + 1), grader)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['id'], len(self.starting_graders))
        del obj['id']
        self.assertEqual(obj, grader)
        current_graders = CourseGradingModel.fetch(self.course_locator).graders
        self.assertEqual(len(self.starting_graders) + 1, len(current_graders))
