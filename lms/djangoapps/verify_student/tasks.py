from djcelery import celery
from verify_student.models import SoftwareSecurePhotoVerification

@celery.task
def retry_failed_photo_verifications():
	"""
	This method finds those PhotoVerifications with a status of
	MUST_RETRY and attempts to verify them.
	"""
	attempts_to_retry = SoftwareSecurePhotoVerification.objects.filter(status='must_retry')
	for attempt in attempts_to_retry:
		attempt.submit()
