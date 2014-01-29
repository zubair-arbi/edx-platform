"""Tests for items views."""

import json
from datetime import datetime
import ddt

from mock import patch
from pytz import UTC
from webob import Response

from django.http import Http404
from django.test import TestCase
from django.test.client import RequestFactory

from contentstore.views.component import component_handler

from contentstore.tests.utils import CourseTestCase
from student.tests.factories import UserFactory
from xmodule.capa_module import CapaDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.django import loc_mapper
from xmodule.modulestore.locator import BlockUsageLocator
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore import Location


class ItemTest(CourseTestCase):
    """ Base test class for create, save, and delete """
    def setUp(self):
        super(ItemTest, self).setUp()

        self.course_locator = loc_mapper().translate_location(
            self.course.location.course_id, self.course.location, False, True
        )
        self.unicode_locator = unicode(self.course_locator)

    def get_old_id(self, locator):
        """
        Converts new locator to old id format (forcing to non-draft).
        """
        return loc_mapper().translate_locator_to_location(BlockUsageLocator(locator)).replace(revision=None)

    def get_item_from_modulestore(self, locator, draft=False):
        """
        Get the item referenced by the locator from the modulestore
        """
        store = modulestore('draft') if draft else modulestore('direct')
        return store.get_item(self.get_old_id(locator))

    def response_locator(self, response):
        """
        Get the locator (unicode representation) from the response payload
        :param response:
        """
        parsed = json.loads(response.content)
        return parsed['locator']

    def create_xblock(self, parent_locator=None, display_name=None, category=None, boilerplate=None):
        data = {
            'parent_locator': self.unicode_locator if parent_locator is None else parent_locator,
            'category': category
        }
        if display_name is not None:
            data['display_name'] = display_name
        if boilerplate is not None:
            data['boilerplate'] = boilerplate
        return self.client.ajax_post('/xblock', json.dumps(data))


class GetItem(ItemTest):
    """Tests for '/xblock' GET url."""

    def test_get_vertical(self):
        # Add a vertical
        resp = self.create_xblock(category='vertical')
        self.assertEqual(resp.status_code, 200)

        # Retrieve it
        resp_content = json.loads(resp.content)
        resp = self.client.get('/xblock/' + resp_content['locator'])
        self.assertEqual(resp.status_code, 200)


class DeleteItem(ItemTest):
    """Tests for '/xblock' DELETE url."""
    def test_delete_static_page(self):
        # Add static tab
        resp = self.create_xblock(category='static_tab')
        self.assertEqual(resp.status_code, 200)

        # Now delete it. There was a bug that the delete was failing (static tabs do not exist in draft modulestore).
        resp_content = json.loads(resp.content)
        resp = self.client.delete('/xblock/' + resp_content['locator'])
        self.assertEqual(resp.status_code, 204)


class TestCreateItem(ItemTest):
    """
    Test the create_item handler thoroughly
    """
    def test_create_nicely(self):
        """
        Try the straightforward use cases
        """
        # create a chapter
        display_name = 'Nicely created'
        resp = self.create_xblock(display_name=display_name, category='chapter')
        self.assertEqual(resp.status_code, 200)

        # get the new item and check its category and display_name
        chap_locator = self.response_locator(resp)
        new_obj = self.get_item_from_modulestore(chap_locator)
        self.assertEqual(new_obj.scope_ids.block_type, 'chapter')
        self.assertEqual(new_obj.display_name, display_name)
        self.assertEqual(new_obj.location.org, self.course.location.org)
        self.assertEqual(new_obj.location.course, self.course.location.course)

        # get the course and ensure it now points to this one
        course = self.get_item_from_modulestore(self.unicode_locator)
        self.assertIn(self.get_old_id(chap_locator).url(), course.children)

        # use default display name
        resp = self.create_xblock(parent_locator=chap_locator, category='vertical')
        self.assertEqual(resp.status_code, 200)

        vert_locator = self.response_locator(resp)

        # create problem w/ boilerplate
        template_id = 'multiplechoice.yaml'
        resp = self.create_xblock(
            parent_locator=vert_locator,
            category='problem',
            boilerplate=template_id
        )
        self.assertEqual(resp.status_code, 200)
        prob_locator = self.response_locator(resp)
        problem = self.get_item_from_modulestore(prob_locator, True)
        # ensure it's draft
        self.assertTrue(problem.is_draft)
        # check against the template
        template = CapaDescriptor.get_template(template_id)
        self.assertEqual(problem.data, template['data'])
        self.assertEqual(problem.display_name, template['metadata']['display_name'])
        self.assertEqual(problem.markdown, template['metadata']['markdown'])

    def test_create_item_negative(self):
        """
        Negative tests for create_item
        """
        # non-existent boilerplate: creates a default
        resp = self.create_xblock(category='problem', boilerplate='nosuchboilerplate.yaml')
        self.assertEqual(resp.status_code, 200)

    def test_create_with_future_date(self):
        self.assertEqual(self.course.start, datetime(2030, 1, 1, tzinfo=UTC))
        resp = self.create_xblock(category='chapter')
        locator = self.response_locator(resp)
        obj = self.get_item_from_modulestore(locator)
        self.assertEqual(obj.start, datetime(2030, 1, 1, tzinfo=UTC))


class TestDuplicateItem(ItemTest):
    """
    Test the duplicate method.
    """
    def setUp(self):
        """ Creates the test course structure and a few components to 'duplicate'. """
        super(TestDuplicateItem, self).setUp()
        # Create a parent chapter (for testing children of children).
        resp = self.create_xblock(parent_locator=self.unicode_locator, category='chapter')
        self.chapter_locator = self.response_locator(resp)

        # create a sequential containing a problem and an html component
        resp = self.create_xblock(parent_locator=self.chapter_locator, category='sequential')
        self.seq_locator = self.response_locator(resp)

        # create problem and an html component
        resp = self.create_xblock(parent_locator=self.seq_locator, category='problem', boilerplate='multiplechoice.yaml')
        self.problem_locator = self.response_locator(resp)

        resp = self.create_xblock(parent_locator=self.seq_locator, category='html')
        self.html_locator = self.response_locator(resp)

        # Create a second sequential just (testing children of children)
        self.create_xblock(parent_locator=self.chapter_locator, category='sequential2')

    def test_duplicate_equality(self):
        """
        Tests that a duplicated xblock is identical to the original,
        except for location and display name.
        """
        def duplicate_and_verify(source_locator, parent_locator):
            locator = self._duplicate_item(parent_locator, source_locator)
            self.assertTrue(check_equality(source_locator, locator), "Duplicated item differs from original")

        def check_equality(source_locator, duplicate_locator):
            original_item = self.get_item_from_modulestore(source_locator, draft=True)
            duplicated_item = self.get_item_from_modulestore(duplicate_locator, draft=True)

            self.assertNotEqual(
                original_item.location,
                duplicated_item.location,
                "Location of duplicate should be different from original"
            )
            # Set the location and display name to be the same so we can make sure the rest of the duplicate is equal.
            duplicated_item.location = original_item.location
            duplicated_item.display_name = original_item.display_name

            # Children will also be duplicated, so for the purposes of testing equality, we will set
            # the children to the original after recursively checking the children.
            if original_item.has_children:
                self.assertEqual(
                    len(original_item.children),
                    len(duplicated_item.children),
                    "Duplicated item differs in number of children"
                )
                for i in xrange(len(original_item.children)):
                    source_locator = loc_mapper().translate_location(
                        self.course.location.course_id, Location(original_item.children[i]), False, True
                    )
                    duplicate_locator = loc_mapper().translate_location(
                        self.course.location.course_id, Location(duplicated_item.children[i]), False, True
                    )
                    if not check_equality(source_locator, duplicate_locator):
                        return False
                duplicated_item.children = original_item.children

            return original_item == duplicated_item

        duplicate_and_verify(self.problem_locator, self.seq_locator)
        duplicate_and_verify(self.html_locator, self.seq_locator)
        duplicate_and_verify(self.seq_locator, self.chapter_locator)
        duplicate_and_verify(self.chapter_locator, self.unicode_locator)

    def test_ordering(self):
        """
        Tests the a duplicated xblock appears immediately after its source
        (if duplicate and source share the same parent), else at the
        end of the children of the parent.
        """
        def verify_order(source_locator, parent_locator, source_position=None):
            locator = self._duplicate_item(parent_locator, source_locator)
            parent = self.get_item_from_modulestore(parent_locator)
            children = parent.children
            if source_position is None:
                self.assertFalse(source_locator in children, 'source item not expected in children array')
                self.assertEqual(
                    children[len(children) - 1],
                    self.get_old_id(locator).url(),
                    "duplicated item not at end"
                )
            else:
                self.assertEqual(
                    children[source_position],
                    self.get_old_id(source_locator).url(),
                    "source item at wrong position"
                )
                self.assertEqual(
                    children[source_position + 1],
                    self.get_old_id(locator).url(),
                    "duplicated item not ordered after source item"
                )

        verify_order(self.problem_locator, self.seq_locator, 0)
        # 2 because duplicate of problem should be located before.
        verify_order(self.html_locator, self.seq_locator, 2)
        verify_order(self.seq_locator, self.chapter_locator, 0)

        # Test duplicating something into a location that is not the parent of the original item.
        # Duplicated item should appear at the end.
        verify_order(self.html_locator, self.unicode_locator)

    def test_display_name(self):
        """
        Tests the expected display name for the duplicated xblock.
        """
        def verify_name(source_locator, parent_locator, expected_name, display_name=None):
            locator = self._duplicate_item(parent_locator, source_locator, display_name)
            duplicated_item = self.get_item_from_modulestore(locator, draft=True)
            self.assertEqual(duplicated_item.display_name, expected_name)
            return locator

        # Display name comes from template.
        dupe_locator = verify_name(self.problem_locator, self.seq_locator, "Duplicate of 'Multiple Choice'")
        # Test dupe of dupe.
        verify_name(dupe_locator, self.seq_locator, "Duplicate of 'Duplicate of 'Multiple Choice''")

        # Uses default display_name of 'Text' from HTML component.
        verify_name(self.html_locator, self.seq_locator, "Duplicate of 'Text'")

        # The sequence does not have a display_name set, so category is shown.
        verify_name(self.seq_locator, self.chapter_locator, "Duplicate of sequential")

        # Now send a custom display name for the duplicate.
        verify_name(self.seq_locator, self.chapter_locator, "customized name", display_name="customized name")

    def _duplicate_item(self, parent_locator, source_locator, display_name=None):
        data = {
            'parent_locator': parent_locator,
            'duplicate_source_locator': source_locator
        }
        if display_name is not None:
            data['display_name'] = display_name

        resp = self.client.ajax_post('/xblock', json.dumps(data))
        resp_content = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        return resp_content['locator']


class TestEditItem(ItemTest):
    """
    Test xblock update.
    """
    def setUp(self):
        """ Creates the test course structure and a couple problems to 'edit'. """
        super(TestEditItem, self).setUp()
        # create a chapter
        display_name = 'chapter created'
        resp = self.create_xblock(display_name=display_name, category='chapter')
        chap_locator = self.response_locator(resp)
        resp = self.create_xblock(parent_locator=chap_locator, category='sequential')
        self.seq_locator = self.response_locator(resp)
        self.seq_update_url = '/xblock/' + self.seq_locator

        # create problem w/ boilerplate
        template_id = 'multiplechoice.yaml'
        resp = self.create_xblock(parent_locator=self.seq_locator, category='problem', boilerplate=template_id)
        self.problem_locator = self.response_locator(resp)
        self.problem_update_url = '/xblock/' + self.problem_locator

        self.course_update_url = '/xblock/' + self.unicode_locator

    def test_delete_field(self):
        """
        Sending null in for a field 'deletes' it
        """
        self.client.ajax_post(
            self.problem_update_url,
            data={'metadata': {'rerandomize': 'onreset'}}
        )
        problem = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertEqual(problem.rerandomize, 'onreset')
        self.client.ajax_post(
            self.problem_update_url,
            data={'metadata': {'rerandomize': None}}
        )
        problem = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertEqual(problem.rerandomize, 'never')

    def test_null_field(self):
        """
        Sending null in for a field 'deletes' it
        """
        problem = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertIsNotNone(problem.markdown)
        self.client.ajax_post(
            self.problem_update_url,
            data={'nullout': ['markdown']}
        )
        problem = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertIsNone(problem.markdown)

    def test_date_fields(self):
        """
        Test setting due & start dates on sequential
        """
        sequential = self.get_item_from_modulestore(self.seq_locator)
        self.assertIsNone(sequential.due)
        self.client.ajax_post(
            self.seq_update_url,
            data={'metadata': {'due': '2010-11-22T04:00Z'}}
        )
        sequential = self.get_item_from_modulestore(self.seq_locator)
        self.assertEqual(sequential.due, datetime(2010, 11, 22, 4, 0, tzinfo=UTC))
        self.client.ajax_post(
            self.seq_update_url,
            data={'metadata': {'start': '2010-09-12T14:00Z'}}
        )
        sequential = self.get_item_from_modulestore(self.seq_locator)
        self.assertEqual(sequential.due, datetime(2010, 11, 22, 4, 0, tzinfo=UTC))
        self.assertEqual(sequential.start, datetime(2010, 9, 12, 14, 0, tzinfo=UTC))

    def test_delete_child(self):
        """
        Test deleting a child.
        """
        # Create 2 children of main course.
        resp_1 = self.create_xblock(display_name='child 1', category='chapter')
        resp_2 = self.create_xblock(display_name='child 2', category='chapter')
        chapter1_locator = self.response_locator(resp_1)
        chapter2_locator = self.response_locator(resp_2)

        course = self.get_item_from_modulestore(self.unicode_locator)
        self.assertIn(self.get_old_id(chapter1_locator).url(), course.children)
        self.assertIn(self.get_old_id(chapter2_locator).url(), course.children)

        # Remove one child from the course.
        resp = self.client.ajax_post(
            self.course_update_url,
            data={'children': [chapter2_locator]}
        )
        self.assertEqual(resp.status_code, 200)

        # Verify that the child is removed.
        course = self.get_item_from_modulestore(self.unicode_locator)
        self.assertNotIn(self.get_old_id(chapter1_locator).url(), course.children)
        self.assertIn(self.get_old_id(chapter2_locator).url(), course.children)

    def test_reorder_children(self):
        """
        Test reordering children that can be in the draft store.
        """
        # Create 2 child units and re-order them. There was a bug about @draft getting added
        # to the IDs.
        unit_1_resp = self.create_xblock(parent_locator=self.seq_locator, category='vertical')
        unit_2_resp = self.create_xblock(parent_locator=self.seq_locator, category='vertical')
        unit1_locator = self.response_locator(unit_1_resp)
        unit2_locator = self.response_locator(unit_2_resp)

        # The sequential already has a child defined in the setUp (a problem).
        # Children must be on the sequential to reproduce the original bug,
        # as it is important that the parent (sequential) NOT be in the draft store.
        children = self.get_item_from_modulestore(self.seq_locator).children
        self.assertEqual(self.get_old_id(unit1_locator).url(), children[1])
        self.assertEqual(self.get_old_id(unit2_locator).url(), children[2])

        resp = self.client.ajax_post(
            self.seq_update_url,
            data={'children': [self.problem_locator, unit2_locator, unit1_locator]}
        )
        self.assertEqual(resp.status_code, 200)

        children = self.get_item_from_modulestore(self.seq_locator).children
        self.assertEqual(self.get_old_id(self.problem_locator).url(), children[0])
        self.assertEqual(self.get_old_id(unit1_locator).url(), children[2])
        self.assertEqual(self.get_old_id(unit2_locator).url(), children[1])

    def test_make_public(self):
        """ Test making a private problem public (publishing it). """
        # When the problem is first created, it is only in draft (because of its category).
        with self.assertRaises(ItemNotFoundError):
            self.get_item_from_modulestore(self.problem_locator, False)
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_public'}
        )
        self.assertIsNotNone(self.get_item_from_modulestore(self.problem_locator, False))

    def test_make_private(self):
        """ Test making a public problem private (un-publishing it). """
        # Make problem public.
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_public'}
        )
        self.assertIsNotNone(self.get_item_from_modulestore(self.problem_locator, False))
        # Now make it private
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_private'}
        )
        with self.assertRaises(ItemNotFoundError):
            self.get_item_from_modulestore(self.problem_locator, False)

    def test_make_draft(self):
        """ Test creating a draft version of a public problem. """
        # Make problem public.
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_public'}
        )
        self.assertIsNotNone(self.get_item_from_modulestore(self.problem_locator, False))
        # Now make it draft, which means both versions will exist.
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'create_draft'}
        )
        # Update the draft version and check that published is different.
        self.client.ajax_post(
            self.problem_update_url,
            data={'metadata': {'due': '2077-10-10T04:00Z'}}
        )
        published = self.get_item_from_modulestore(self.problem_locator, False)
        self.assertIsNone(published.due)
        draft = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertEqual(draft.due, datetime(2077, 10, 10, 4, 0, tzinfo=UTC))

    def test_make_public_with_update(self):
        """ Update a problem and make it public at the same time. """
        self.client.ajax_post(
            self.problem_update_url,
            data={
                'metadata': {'due': '2077-10-10T04:00Z'},
                'publish': 'make_public'
            }
        )
        published = self.get_item_from_modulestore(self.problem_locator, False)
        self.assertEqual(published.due, datetime(2077, 10, 10, 4, 0, tzinfo=UTC))

    def test_make_private_with_update(self):
        """ Make a problem private and update it at the same time. """
        # Make problem public.
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_public'}
        )
        self.client.ajax_post(
            self.problem_update_url,
            data={
                'metadata': {'due': '2077-10-10T04:00Z'},
                'publish': 'make_private'
            }
        )
        with self.assertRaises(ItemNotFoundError):
            self.get_item_from_modulestore(self.problem_locator, False)
        draft = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertEqual(draft.due, datetime(2077, 10, 10, 4, 0, tzinfo=UTC))

    def test_create_draft_with_update(self):
        """ Create a draft and update it at the same time. """
        # Make problem public.
        self.client.ajax_post(
            self.problem_update_url,
            data={'publish': 'make_public'}
        )
        self.assertIsNotNone(self.get_item_from_modulestore(self.problem_locator, False))
        # Now make it draft, which means both versions will exist.
        self.client.ajax_post(
            self.problem_update_url,
            data={
                'metadata': {'due': '2077-10-10T04:00Z'},
                'publish': 'create_draft'
            }
        )
        published = self.get_item_from_modulestore(self.problem_locator, False)
        self.assertIsNone(published.due)
        draft = self.get_item_from_modulestore(self.problem_locator, True)
        self.assertEqual(draft.due, datetime(2077, 10, 10, 4, 0, tzinfo=UTC))


@ddt.ddt
class TestComponentHandler(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

        patcher = patch('contentstore.views.component.modulestore')
        self.modulestore = patcher.start()
        self.addCleanup(patcher.stop)

        self.descriptor = self.modulestore.return_value.get_item.return_value

        self.usage_id = 'dummy_usage_id'

        self.user = UserFactory()

        self.request = self.request_factory.get('/dummy-url')
        self.request.user = self.user

    def test_invalid_handler(self):
        self.descriptor.handle.side_effect = Http404

        with self.assertRaises(Http404):
            component_handler(self.request, self.usage_id, 'invalid_handler')

    @ddt.data('GET', 'POST', 'PUT', 'DELETE')
    def test_request_method(self, method):

        def check_handler(handler, request, suffix):
            self.assertEquals(request.method, method)
            return Response()

        self.descriptor.handle = check_handler

        # Have to use the right method to create the request to get the HTTP method that we want
        req_factory_method = getattr(self.request_factory, method.lower())
        request = req_factory_method('/dummy-url')
        request.user = self.user

        component_handler(request, self.usage_id, 'dummy_handler')

    @ddt.data(200, 404, 500)
    def test_response_code(self, status_code):
        def create_response(handler, request, suffix):
            return Response(status_code=status_code)

        self.descriptor.handle = create_response

        self.assertEquals(component_handler(self.request, self.usage_id, 'dummy_handler').status_code, status_code)
