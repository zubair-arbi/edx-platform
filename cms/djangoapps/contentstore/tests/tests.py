"""
This test file will test registration, login, activation, and session activity timeouts
"""
import time

from django.test.utils import override_settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings

from contentstore.tests.utils import parse_json, user, registration, AjaxEnabledTestClient
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from contentstore.tests.test_course_settings import CourseTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from contentstore.tests.modulestore_config import TEST_MODULESTORE
import datetime
from pytz import UTC


@override_settings(MODULESTORE=TEST_MODULESTORE)
class ContentStoreTestCase(ModuleStoreTestCase):
    def _login(self, email, password):
        """
        Login.  View should always return 200.  The success/fail is in the
        returned json
        """
        resp = self.client.post(
            reverse('login_post'),
            {'email': email, 'password': password}
        )
        self.assertEqual(resp.status_code, 200)
        return resp

    def login(self, email, password):
        """Login, check that it worked."""
        resp = self._login(email, password)
        data = parse_json(resp)
        self.assertTrue(data['success'])
        return resp

    def _create_account(self, username, email, password):
        """Try to create an account.  No error checking"""
        resp = self.client.post('/create_account', {
            'username': username,
            'email': email,
            'password': password,
            'location': 'home',
            'language': 'Franglish',
            'name': 'Fred Weasley',
            'terms_of_service': 'true',
            'honor_code': 'true',
        })
        return resp

    def create_account(self, username, email, password):
        """Create the account and check that it worked"""
        resp = self._create_account(username, email, password)
        self.assertEqual(resp.status_code, 200)
        data = parse_json(resp)
        self.assertEqual(data['success'], True)

        # Check both that the user is created, and inactive
        self.assertFalse(user(email).is_active)

        return resp

    def _activate_user(self, email):
        """Look up the activation key for the user, then hit the activate view.
        No error checking"""
        activation_key = registration(email).activation_key

        # and now we try to activate
        resp = self.client.get(reverse('activate', kwargs={'key': activation_key}))
        return resp

    def activate_user(self, email):
        resp = self._activate_user(email)
        self.assertEqual(resp.status_code, 200)
        # Now make sure that the user is now actually activated
        self.assertTrue(user(email).is_active)


class AuthTestCase(ContentStoreTestCase):
    """Check that various permissions-related things work"""

    def setUp(self):
        self.email = 'a@b.com'
        self.pw = 'xyz'
        self.username = 'testuser'
        self.client = AjaxEnabledTestClient()
        # clear the cache so ratelimiting won't affect these tests
        cache.clear()

    def check_page_get(self, url, expected):
        resp = self.client.get_html(url)
        self.assertEqual(resp.status_code, expected)
        return resp

    def test_public_pages_load(self):
        """Make sure pages that don't require login load without error."""
        pages = (
            reverse('login'),
            reverse('signup'),
        )
        for page in pages:
            print("Checking '{0}'".format(page))
            self.check_page_get(page, 200)

    def test_create_account_errors(self):
        # No post data -- should fail
        resp = self.client.post('/create_account', {})
        self.assertEqual(resp.status_code, 200)
        data = parse_json(resp)
        self.assertEqual(data['success'], False)

    def test_create_account(self):
        self.create_account(self.username, self.email, self.pw)
        self.activate_user(self.email)

    def test_login(self):
        self.create_account(self.username, self.email, self.pw)

        # Not activated yet.  Login should fail.
        resp = self._login(self.email, self.pw)
        data = parse_json(resp)
        self.assertFalse(data['success'])

        self.activate_user(self.email)

        # Now login should work
        self.login(self.email, self.pw)

    def test_login_ratelimited(self):
        # try logging in 30 times, the default limit in the number of failed
        # login attempts in one 5 minute period before the rate gets limited
        for i in xrange(30):
            resp = self._login(self.email, 'wrong_password{0}'.format(i))
            self.assertEqual(resp.status_code, 200)
        resp = self._login(self.email, 'wrong_password')
        self.assertEqual(resp.status_code, 200)
        data = parse_json(resp)
        self.assertFalse(data['success'])
        self.assertIn('Too many failed login attempts.', data['value'])

    def test_login_link_on_activation_age(self):
        self.create_account(self.username, self.email, self.pw)
        # we want to test the rendering of the activation page when the user isn't logged in
        self.client.logout()
        resp = self._activate_user(self.email)
        self.assertEqual(resp.status_code, 200)

        # check the the HTML has links to the right login page. Note that this is merely a content
        # check and thus could be fragile should the wording change on this page
        expected = 'You can now <a href="' + reverse('login') + '">login</a>.'
        self.assertIn(expected, resp.content)

    def test_private_pages_auth(self):
        """Make sure pages that do require login work."""
        auth_pages = (
            '/course',
        )

        # These are pages that should just load when the user is logged in
        # (no data needed)
        simple_auth_pages = (
            '/course',
        )

        # need an activated user
        self.test_create_account()

        # Create a new session
        self.client = AjaxEnabledTestClient()

        # Not logged in.  Should redirect to login.
        print('Not logged in')
        for page in auth_pages:
            print("Checking '{0}'".format(page))
            self.check_page_get(page, expected=302)

        # Logged in should work.
        self.login(self.email, self.pw)

        print('Logged in')
        for page in simple_auth_pages:
            print("Checking '{0}'".format(page))
            self.check_page_get(page, expected=200)

    def test_index_auth(self):

        # not logged in.  Should return a redirect.
        resp = self.client.get_html('/course')
        self.assertEqual(resp.status_code, 302)

        # Logged in should work.

    @override_settings(SESSION_INACTIVITY_TIMEOUT_IN_SECONDS=1)
    def test_inactive_session_timeout(self):
        """
        Verify that an inactive session times out and redirects to the
        login page
        """
        self.create_account(self.username, self.email, self.pw)
        self.activate_user(self.email)

        self.login(self.email, self.pw)

        # make sure we can access courseware immediately
        resp = self.client.get_html('/course')
        self.assertEquals(resp.status_code, 200)

        # then wait a bit and see if we get timed out
        time.sleep(2)

        resp = self.client.get_html('/course')

        # re-request, and we should get a redirect to login page
        self.assertRedirects(resp, settings.LOGIN_REDIRECT_URL + '?next=/course')


class ForumTestCase(CourseTestCase):
    def setUp(self):
        """ Creates the test course. """
        super(ForumTestCase, self).setUp()
        self.course = CourseFactory.create(org='testX', number='727', display_name='Forum Course')

    def test_blackouts(self):
        now = datetime.datetime.now(UTC)
        times1 = [
            (now - datetime.timedelta(days=14), now - datetime.timedelta(days=11)),
            (now + datetime.timedelta(days=24), now + datetime.timedelta(days=30))
        ]
        self.course.discussion_blackouts = [(t.isoformat(), t2.isoformat()) for t, t2 in times1]
        self.assertTrue(self.course.forum_posts_allowed)
        times2 = [
            (now - datetime.timedelta(days=14), now + datetime.timedelta(days=2)),
            (now + datetime.timedelta(days=24), now + datetime.timedelta(days=30))
        ]
        self.course.discussion_blackouts = [(t.isoformat(), t2.isoformat()) for t, t2 in times2]
        self.assertFalse(self.course.forum_posts_allowed)
