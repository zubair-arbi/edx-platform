class UrlForUserTest(TestCase):

    def setUp(self):

        self.content = {'course_id':'edX/full/6.002_Spring_2012'}
        self.user_id = None
    
    def test_url_for_user(self.content, self.user_id):

        self.assertEqual(urlreselvers.resolve(urlresolvers.reverse('django_comment_client.forum.views.user_profile', args=[self.content['course_id'], self.user_id])))

