from courseware import grades, courses
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand, CommandError
import os
from django.contrib.auth.models import User
from optparse import make_option
import datetime


class Command(BaseCommand):

    help = """
    Generate a list of grades for all students
    that are enrolled in a course.

    Outputs grades to a text file with a single
    grade per line, no user informatoin is included.
    """

    option_list = BaseCommand.option_list + (
        make_option('-c', '--course',
                    metavar='COURSE_ID',
                    dest='course',
                    default=False,
                    help='Grade and generate certificates for a specific '
                         'course'),
        make_option('-o', '--output',
                    metavar='FILE',
                    dest='output',
                    default=False,
                    help='Filename for grade output'))

    def handle(self, *args, **options):
        if os.path.exists(options['output']):
            raise CommandError("File {0} already exists".format(
                options['output']))

        STATUS_INTERVAL = 500
        course_id = options['course']
        print "Fetching enrolled students for {0}".format(course_id)
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=course_id).prefetch_related(
                "groups").order_by('username')
        factory = RequestFactory()
        request = factory.get('/')
        total = enrolled_students.count()
        print "Total enrolled: {0}".format(total)
        course = courses.get_course_by_id(course_id)
        total = enrolled_students.count()
        count = 0
        start = datetime.datetime.now()
        for student in enrolled_students:
            count += 1
            if count % STATUS_INTERVAL == 0:
                # Print a status update with an approximation of
                # how much time is left based on how long the last
                # interval took
                diff = datetime.datetime.now() - start
                timeleft = diff * (total - count) / STATUS_INTERVAL
                hours, remainder = divmod(timeleft.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                print "{0}/{1} completed ~{2:02}:{3:02}m remaining".format(
                    count, total, hours, minutes)
                start = datetime.datetime.now()
            grade = grades.grade(student, request, course)
            with open(options['output'], 'a') as f:
                f.write(str(grade['percent']) + '\n')
