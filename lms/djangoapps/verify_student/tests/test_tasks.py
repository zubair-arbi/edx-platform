# -*- coding: utf-8 -*-
import json
from nose.tools import (
    assert_equals, assert_true
)
from mock import patch
from django.test import TestCase
from django.conf import settings
import requests
import requests.exceptions

from student.tests.factories import UserFactory
from verify_student.models import SoftwareSecurePhotoVerification
from verify_student.tasks import retry_failed_photo_verifications

FAKE_SETTINGS = {
    "SOFTWARE_SECURE": {
        "FACE_IMAGE_AES_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "API_ACCESS_KEY": "BBBBBBBBBBBBBBBBBBBB",
        "API_SECRET_KEY": "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        "RSA_PUBLIC_KEY": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu2fUn20ZQtDpa1TKeCA/
rDA2cEeFARjEr41AP6jqP/k3O7TeqFX6DgCBkxcjojRCs5IfE8TimBHtv/bcSx9o
7PANTq/62ZLM9xAMpfCcU6aAd4+CVqQkXSYjj5TUqamzDFBkp67US8IPmw7I2Gaa
tX8ErZ9D7ieOJ8/0hEiphHpCZh4TTgGuHgjon6vMV8THtq3AQMaAQ/y5R3V7Lezw
dyZCM9pBcvcH+60ma+nNg8GVGBAW/oLxILBtg+T3PuXSUvcu/r6lUFMHk55pU94d
9A/T8ySJm379qU24ligMEetPk1o9CUasdaI96xfXVDyFhrzrntAmdD+HYCSPOQHz
iwIDAQAB
-----END PUBLIC KEY-----""",
        "API_URL": "http://localhost/verify_student/fake_endpoint",
        "AWS_ACCESS_KEY": "FAKEACCESSKEY",
        "AWS_SECRET_KEY": "FAKESECRETKEY",
        "S3_BUCKET": "fake-bucket"
    }
}


class MockKey(object):
    """
    Mocking a boto S3 Key object. It's a really dumb mock because once we
    write data to S3, we never read it again. We simply generate a link to it
    and pass that to Software Secure. Because of that, we don't even implement
    the ability to pull back previously written content in this mock.

    Testing that the encryption/decryption roundtrip on the data works is in
    test_ssencrypt.py
    """
    def __init__(self, bucket):
        self.bucket = bucket

    def set_contents_from_string(self, contents):
        self.contents = contents

    def generate_url(self, duration):  # TODO suppress pylint here
        return "http://fake-edx-s3.edx.org/"


class MockBucket(object):
    """Mocking a boto S3 Bucket object."""
    def __init__(self, name):
        self.name = name


class MockS3Connection(object):
    """Mocking a boto S3 Connection"""
    def __init__(self, access_key, secret_key):
        pass

    def get_bucket(self, bucket_name):
        return MockBucket(bucket_name)

def mock_software_secure_post(url, headers=None, data=None, **kwargs):
    """
    Mocks our interface when we post to Software Secure. Does basic assertions
    on the fields we send over to make sure we're not missing headers or giving
    total garbage.
    """
    data_dict = json.loads(data)

    # Basic sanity checking on the keys
    EXPECTED_KEYS = [
        "EdX-ID", "ExpectedName", "PhotoID", "PhotoIDKey", "SendResponseTo",
        "UserPhoto", "UserPhotoKey",
    ]
    for key in EXPECTED_KEYS:
        assert_true(
            data_dict.get(key),
            "'{}' must be present and not blank in JSON submitted to Software Secure".format(key)
        )

    # The keys should be stored as Base64 strings, i.e. this should not explode
    data_dict["PhotoIDKey"].decode("base64")
    data_dict["UserPhotoKey"].decode("base64")

    response = requests.Response()
    response.status_code = 200

    return response

def mock_software_secure_post_error(url, headers=None, data=None, **kwargs):
    """
    Simulates what happens if our post to Software Secure is rejected, for
    whatever reason.
    """
    response = requests.Response()
    response.status_code = 400
    return response

def mock_software_secure_post_unavailable(url, headers=None, data=None, **kwargs):
    """Simulates a connection failure when we try to submit to Software Secure."""
    raise requests.exceptions.ConnectionError


# Lots of patching to stub in our own settings, S3 substitutes, and HTTP posting
@patch.dict(settings.VERIFY_STUDENT, FAKE_SETTINGS)
@patch('verify_student.models.S3Connection', new=MockS3Connection)
@patch('verify_student.models.Key', new=MockKey)
@patch('verify_student.models.requests.post', new=mock_software_secure_post)
class TestVerifyStudentTask(TestCase):
    """
    Tests for tasks in the verify_student module
    """

    def create_and_submit(self, username):
        """
        Helper method that lets us create new SoftwareSecurePhotoVerifications
        """
        user = UserFactory.create()
        attempt = SoftwareSecurePhotoVerification(user=user)
        user.profile.name = username
        attempt.upload_face_image("Fake Data")
        attempt.upload_photo_id_image("More Fake Data")
        attempt.mark_ready()
        attempt.submit()
        return attempt

    def test_retry_failed_photo_verifications(self):
        """
        Tests that the task used to find "must_retry" SoftwareSecurePhotoVerifications
        and re-submit them executes successfully
        """
        # set up some fake data to use...
        self.create_and_submit("SuccessfulSally")
        self.create_and_submit("SuccessfulSue")
        with patch('verify_student.models.requests.post', new=mock_software_secure_post_error):
            self.create_and_submit("RetryRoger")
        with patch('verify_student.models.requests.post', new=mock_software_secure_post_error):
            self.create_and_submit("RetryRick")
        # check to make sure we had two successes and two failures; otherwise we've got problems elsewhere
        assert_equals(len(SoftwareSecurePhotoVerification.objects.filter(status="submitted")), 2)
        assert_equals(len(SoftwareSecurePhotoVerification.objects.filter(status='must_retry')), 2)
        retry_failed_photo_verifications()
        attempts_to_retry = SoftwareSecurePhotoVerification.objects.filter(status='must_retry')
        assert_equals(bool(attempts_to_retry), False)
