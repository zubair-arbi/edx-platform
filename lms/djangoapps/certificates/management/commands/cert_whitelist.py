from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from certificates.models import CertificateWhitelist
from django.contrib.auth.models import User


class Command(BaseCommand):

    help = """
    Sets or gets the certificate whitelist for a given
    user/course

        Add a user to the whitelist for a course

        $ ... cert_whitelist --add joe -c "MITx/6.002x/2012_Fall"

        Remove a user from the whitelist for a course

        $ ... cert_whitelist --del joe -c "MITx/6.002x/2012_Fall"

        Print out who is whitelisted for a course

        $ ... cert_whitelist -c "MITx/6.002x/2012_Fall"

    """

    option_list = BaseCommand.option_list + (
        make_option('-a', '--add',
                    metavar='USER',
                    dest='add',
                    default=False,
                    help='user to add to the certificate whitelist'),

        make_option('-d', '--del',
                    metavar='USER',
                    dest='del',
                    default=False,
                    help='user to remove from the certificate whitelist'),

        make_option('-c', '--course-id',
                    metavar='COURSE_ID',
                    dest='course_id',
                    default=False,
                    help="course id to query"),
    )

    def handle(self, *args, **options):
        course_id = options['course_id']
        if not course_id:
            raise CommandError("You must specify a course-id")
        if options['add'] and options['del']:
            raise CommandError("Either remove or add a user, not both")

        if options['add'] or options['del']:
            user_str = options['add'] or options['del']
            if '@' in user_str:
                user = User.objects.get(email=user_str)
            else:
                user = User.objects.get(username=user_str)

            cert_whitelist, created = \
                CertificateWhitelist.objects.get_or_create(
                    user=user, course_id=course_id)
            if options['add']:
                cert_whitelist.whitelist = True
            elif options['del']:
                cert_whitelist.whitelist = False
            cert_whitelist.save()

        whitelist = CertificateWhitelist.objects.filter(course_id=course_id)
        print "User whitelist for course {0}:\n{1}".format(course_id,
              '\n'.join(["{0} {1} {2}".format(
                  u.user.username, u.user.email, u.whitelist)
                  for u in whitelist]))
