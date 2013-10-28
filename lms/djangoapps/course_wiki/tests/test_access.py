
from nose.tools import raises
from django.contrib.auth.models import Group
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from django.test.utils import override_settings
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE

from instructor.access import (allow_access,
                               revoke_access,
                               list_with_level,)

from wiki.models import URLPath, Article
from course_wiki.views import get_or_create_root
from course_wiki.utils import user_is_article_course_staff, course_wiki_slug

@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestWikiStaffStatus(ModuleStoreTestCase):
    """ Test access listings. """
    def setUp(self):

        self.course_math101 = CourseFactory.create(org='org', number='math101', display_name='Course')
        self.course_math101b = CourseFactory.create(org='org', number='math101b', display_name='Course')
        self.course_200 = CourseFactory.create(org='org', number='200', display_name='Course')
        self.course_310b = CourseFactory.create(org='org', number='310b', display_name='Course')
        self.course_310b_ = CourseFactory.create(org='org', number='210b_', display_name='Course')

        self.wiki = get_or_create_root()

        self.wiki_math101 = self.create_urlpath(self.wiki, course_wiki_slug(self.course_math101))
        self.wiki_math101_page = self.create_urlpath(self.wiki_math101, 'Child')
        self.wiki_math101_page_page = self.create_urlpath(self.wiki_math101_page, 'Grandchild')

        self.wiki_200 = self.create_urlpath(self.wiki, course_wiki_slug(self.course_200))
        self.wiki_200_page = self.create_urlpath(self.wiki_200, 'Child')
        self.wiki_200_page_page = self.create_urlpath(self.wiki_200_page, 'Grandchild')

        self.wiki_310b = self.create_urlpath(self.wiki, course_wiki_slug(self.course_310b))
        self.wiki_310b_ = self.create_urlpath(self.wiki, course_wiki_slug(self.course_310b_))

        self.student = UserFactory.create()
        self.instructor1 = UserFactory.create()
        self.instructor2 = UserFactory()
        self.staff2 = UserFactory()
        self.staff1 = UserFactory.create()

    def create_urlpath(self, parent, slug):
        return URLPath.create_article(parent, slug, title=slug)

    def test_no_one_is_root_wiki_staff(self):
        self.assertFalse(user_is_article_course_staff(self.instructor1, self.wiki.article))
        self.assertFalse(user_is_article_course_staff(self.staff1, self.wiki.article))
        self.assertFalse(user_is_article_course_staff(self.student, self.wiki.article))

    def test_student_is_not_course_wiki_staff(self):
        self.assertFalse(user_is_article_course_staff(self.student, self.wiki_math101.article))
        self.assertFalse(user_is_article_course_staff(self.student, self.wiki_math101_page.article))
        self.assertFalse(user_is_article_course_staff(self.student, self.wiki_math101_page_page.article))

    def test_course_staff_is_course_wiki_staff(self):
        allow_access(self.course_math101, self.instructor1, 'instructor')
        allow_access(self.course_math101, self.staff1, 'staff')

        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_math101.article))
        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_math101_page.article))
        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_math101_page_page.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_math101.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_math101_page.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_math101_page_page.article))

    def test_course_staff_is_course_wiki_staff_for_numerical_course_number(self):
        allow_access(self.course_200, self.instructor1, 'instructor')
        allow_access(self.course_200, self.staff1, 'staff')

        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_200.article))
        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_200_page.article))
        self.assertTrue(user_is_article_course_staff(self.instructor1, self.wiki_200_page_page.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_200.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_200_page.article))
        self.assertTrue(user_is_article_course_staff(self.staff1, self.wiki_200_page_page.article))

    def test_other_course_staff_is_not_course_wiki_staff(self):
        allow_access(self.course_math101b, self.instructor2, 'instructor')
        allow_access(self.course_math101b, self.staff2, 'staff')

        self.assertFalse(user_is_article_course_staff(self.instructor2, self.wiki_math101.article))
        self.assertFalse(user_is_article_course_staff(self.instructor2, self.wiki_math101_page.article))
        self.assertFalse(user_is_article_course_staff(self.instructor2, self.wiki_math101_page_page.article))
        self.assertFalse(user_is_article_course_staff(self.staff2, self.wiki_math101.article))
        self.assertFalse(user_is_article_course_staff(self.staff2, self.wiki_math101_page.article))
        self.assertFalse(user_is_article_course_staff(self.staff2, self.wiki_math101_page_page.article))

        allow_access(self.course_310b, self.instructor1, 'instructor')
        allow_access(self.course_310b, self.staff1, 'staff')
        allow_access(self.course_310b_, self.instructor2, 'instructor')
        allow_access(self.course_310b_, self.staff2, 'staff')

        self.assertFalse(user_is_article_course_staff(self.instructor1, self.wiki_310b_.article))
        self.assertFalse(user_is_article_course_staff(self.staff1, self.wiki_310b_.article))

        self.assertFalse(user_is_article_course_staff(self.instructor2, self.wiki_310b.article))
        self.assertFalse(user_is_article_course_staff(self.staff2, self.wiki_310b.article))
