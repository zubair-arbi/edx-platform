from django.test import TestCase
from verify_student.models import SoftwareSecurePhotoVerification
from verify_student.tasks import retry_failed_photo_verifications

class TestVerifyStudentTask(TestCase):
	def setUp(self):
		# todo: make some users who need to retry, and some who don't
		pass

	def test_retry_failed_photo_verifications(self):
		# todo: run the method and make sure we call on only the ones we want
		# make sure failures are logged properly?
		retry_failed_photo_verifications()
		pass