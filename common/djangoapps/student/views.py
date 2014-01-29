"""
Student Views
"""
import datetime
import json
import logging
import random
import re
import string       # pylint: disable=W0402
import urllib
import uuid
import time

from django.conf import settings
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_reset_confirm
# from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.context_processors import csrf
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.validators import validate_email, validate_slug, ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404)
from django.shortcuts import redirect
from django_future.csrf import ensure_csrf_cookie
from django.utils.http import cookie_date, base36_to_int
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST, require_GET
from django.contrib.admin.views.decorators import staff_member_required

from ratelimitbackend.exceptions import RateLimitException

from edxmako.shortcuts import render_to_response, render_to_string

from course_modes.models import CourseMode
from student.models import (
    Registration, UserProfile, PendingNameChange,
    PendingEmailChange, CourseEnrollment, unique_id_for_user,
    CourseEnrollmentAllowed, UserStanding,
)
from student.forms import PasswordResetFormNoActive

from verify_student.models import SoftwareSecurePhotoVerification
from certificates.models import CertificateStatuses, certificate_status_for_student

from xmodule.course_module import CourseDescriptor
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import MONGO_MODULESTORE_TYPE

from collections import namedtuple

from courseware.courses import get_courses, sort_by_announcement
from courseware.access import has_access

from external_auth.models import ExternalAuthMap
import external_auth.views

from bulk_email.models import Optout, CourseAuthorization
import shoppingcart

import track.views

from dogapi import dog_stats_api
from pytz import UTC

from util.json_request import JsonResponse

from microsite_configuration.middleware import MicrositeConfiguration

log = logging.getLogger("edx.student")
AUDIT_LOG = logging.getLogger("audit")

Article = namedtuple('Article', 'title url author image deck publication publish_date')


def csrf_token(context):
    """A csrf token that can be included in a form."""
    csrf_token = context.get('csrf_token', '')
    if csrf_token == 'NOTPROVIDED':
        return ''
    return (u'<div style="display:none"><input type="hidden"'
            ' name="csrfmiddlewaretoken" value="%s" /></div>' % (csrf_token))


# NOTE: This view is not linked to directly--it is called from
# branding/views.py:index(), which is cached for anonymous users.
# This means that it should always return the same thing for anon
# users. (in particular, no switching based on query params allowed)
def index(request, extra_context={}, user=AnonymousUser()):
    """
    Render the edX main page.

    extra_context is used to allow immediate display of certain modal windows, eg signup,
    as used by external_auth.
    """

    # The course selection work is done in courseware.courses.
    domain = settings.FEATURES.get('FORCE_UNIVERSITY_DOMAIN')  # normally False
    # do explicit check, because domain=None is valid
    if domain is False:
        domain = request.META.get('HTTP_HOST')

    courses = get_courses(user, domain=domain)
    courses = sort_by_announcement(courses)

    context = {'courses': courses}

    context.update(extra_context)
    return render_to_response('index.html', context)


def course_from_id(course_id):
    """Return the CourseDescriptor corresponding to this course_id"""
    course_loc = CourseDescriptor.id_to_location(course_id)
    return modulestore().get_instance(course_id, course_loc)

day_pattern = re.compile(r'\s\d+,\s')
multimonth_pattern = re.compile(r'\s?\-\s?\S+\s')


def _get_date_for_press(publish_date):
    # strip off extra months, and just use the first:
    date = re.sub(multimonth_pattern, ", ", publish_date)
    if re.search(day_pattern, date):
        date = datetime.datetime.strptime(date, "%B %d, %Y").replace(tzinfo=UTC)
    else:
        date = datetime.datetime.strptime(date, "%B, %Y").replace(tzinfo=UTC)
    return date


def press(request):
    json_articles = cache.get("student_press_json_articles")
    if json_articles is None:
        if hasattr(settings, 'RSS_URL'):
            content = urllib.urlopen(settings.PRESS_URL).read()
            json_articles = json.loads(content)
        else:
            content = open(settings.PROJECT_ROOT / "templates" / "press.json").read()
            json_articles = json.loads(content)
        cache.set("student_press_json_articles", json_articles)
    articles = [Article(**article) for article in json_articles]
    articles.sort(key=lambda item: _get_date_for_press(item.publish_date), reverse=True)
    return render_to_response('static_templates/press.html', {'articles': articles})


def process_survey_link(survey_link, user):
    """
    If {UNIQUE_ID} appears in the link, replace it with a unique id for the user.
    Currently, this is sha1(user.username).  Otherwise, return survey_link.
    """
    return survey_link.format(UNIQUE_ID=unique_id_for_user(user))


def cert_info(user, course):
    """
    Get the certificate info needed to render the dashboard section for the given
    student and course.  Returns a dictionary with keys:

    'status': one of 'generating', 'ready', 'notpassing', 'processing', 'restricted'
    'show_download_url': bool
    'download_url': url, only present if show_download_url is True
    'show_disabled_download_button': bool -- true if state is 'generating'
    'show_survey_button': bool
    'survey_url': url, only if show_survey_button is True
    'grade': if status is not 'processing'
    """
    if not course.has_ended():
        return {}

    return _cert_info(user, course, certificate_status_for_student(user, course.id))


def _cert_info(user, course, cert_status):
    """
    Implements the logic for cert_info -- split out for testing.
    """
    default_status = 'processing'

    default_info = {'status': default_status,
                    'show_disabled_download_button': False,
                    'show_download_url': False,
                    'show_survey_button': False,
                    }

    if cert_status is None:
        return default_info

    # simplify the status for the template using this lookup table
    template_state = {
        CertificateStatuses.generating: 'generating',
        CertificateStatuses.regenerating: 'generating',
        CertificateStatuses.downloadable: 'ready',
        CertificateStatuses.notpassing: 'notpassing',
        CertificateStatuses.restricted: 'restricted',
    }

    status = template_state.get(cert_status['status'], default_status)

    d = {'status': status,
         'show_download_url': status == 'ready',
         'show_disabled_download_button': status == 'generating',
         'mode': cert_status.get('mode', None)}

    if (status in ('generating', 'ready', 'notpassing', 'restricted') and
            course.end_of_course_survey_url is not None):
        d.update({
            'show_survey_button': True,
            'survey_url': process_survey_link(course.end_of_course_survey_url, user)})
    else:
        d['show_survey_button'] = False

    if status == 'ready':
        if 'download_url' not in cert_status:
            log.warning("User %s has a downloadable cert for %s, but no download url",
                        user.username, course.id)
            return default_info
        else:
            d['download_url'] = cert_status['download_url']

    if status in ('generating', 'ready', 'notpassing', 'restricted'):
        if 'grade' not in cert_status:
            # Note: as of 11/20/2012, we know there are students in this state-- cs169.1x,
            # who need to be regraded (we weren't tracking 'notpassing' at first).
            # We can add a log.warning here once we think it shouldn't happen.
            return default_info
        else:
            d['grade'] = cert_status['grade']

    return d


@ensure_csrf_cookie
def signin_user(request):
    """
    This view will display the non-modal login form
    """
    if (settings.FEATURES['AUTH_USE_MIT_CERTIFICATES'] and
            external_auth.views.ssl_get_cert_from_request(request)):
        # SSL login doesn't require a view, so redirect
        # branding and allow that to process the login if it
        # is enabled and the header is in the request.
        return redirect(reverse('root'))
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))

    context = {
        'course_id': request.GET.get('course_id'),
        'enrollment_action': request.GET.get('enrollment_action'),
        'platform_name': MicrositeConfiguration.get_microsite_configuration_value(
            'platform_name',
            settings.PLATFORM_NAME
        ),
    }
    return render_to_response('login.html', context)


@ensure_csrf_cookie
def register_user(request, extra_context=None):
    """
    This view will display the non-modal registration form
    """
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))
    if settings.FEATURES.get('AUTH_USE_MIT_CERTIFICATES_IMMEDIATE_SIGNUP'):
        # Redirect to branding to process their certificate if SSL is enabled
        # and registration is disabled.
        return redirect(reverse('root'))

    context = {
        'course_id': request.GET.get('course_id'),
        'enrollment_action': request.GET.get('enrollment_action'),
        'platform_name': MicrositeConfiguration.get_microsite_configuration_value(
            'platform_name',
            settings.PLATFORM_NAME
        ),
    }
    if extra_context is not None:
        context.update(extra_context)

    if context.get("extauth_domain", '').startswith(external_auth.views.SHIBBOLETH_DOMAIN_PREFIX):
        return render_to_response('register-shib.html', context)
    return render_to_response('register.html', context)


def complete_course_mode_info(course_id, enrollment):
    """
    We would like to compute some more information from the given course modes
    and the user's current enrollment

    Returns the given information:
        - whether to show the course upsell information
        - numbers of days until they can't upsell anymore
    """
    modes = CourseMode.modes_for_course_dict(course_id)
    mode_info = {'show_upsell': False, 'days_for_upsell': None}
    # we want to know if the user is already verified and if verified is an
    # option
    if 'verified' in modes and enrollment.mode != 'verified':
        mode_info['show_upsell'] = True
        # if there is an expiration date, find out how long from now it is
        if modes['verified'].expiration_datetime:
            today = datetime.datetime.now(UTC).date()
            mode_info['days_for_upsell'] = (modes['verified'].expiration_datetime.date() - today).days

    return mode_info


@login_required
@ensure_csrf_cookie
def dashboard(request):
    user = request.user

    # Build our (course, enrollment) list for the user, but ignore any courses that no
    # longer exist (because the course IDs have changed). Still, we don't delete those
    # enrollments, because it could have been a data push snafu.
    course_enrollment_pairs = []

    # for microsites, we want to filter and only show enrollments for courses within
    # the microsites 'ORG'
    course_org_filter = MicrositeConfiguration.get_microsite_configuration_value('course_org_filter')

    # Let's filter out any courses in an "org" that has been declared to be
    # in a Microsite
    org_filter_out_set = MicrositeConfiguration.get_all_microsite_orgs()

    # remove our current Microsite from the "filter out" list, if applicable
    if course_org_filter:
        org_filter_out_set.remove(course_org_filter)

    for enrollment in CourseEnrollment.enrollments_for_user(user):
        try:
            course = course_from_id(enrollment.course_id)

            # if we are in a Microsite, then filter out anything that is not
            # attributed (by ORG) to that Microsite
            if course_org_filter and course_org_filter != course.location.org:
                continue
            # Conversely, if we are not in a Microsite, then let's filter out any enrollments
            # with courses attributed (by ORG) to Microsites
            elif course.location.org in org_filter_out_set:
                continue

            course_enrollment_pairs.append((course, enrollment))
        except ItemNotFoundError:
            log.error("User {0} enrolled in non-existent course {1}"
                      .format(user.username, enrollment.course_id))

    course_optouts = Optout.objects.filter(user=user).values_list('course_id', flat=True)

    message = ""
    if not user.is_active:
        message = render_to_string('registration/activate_account_notice.html', {'email': user.email})

    # Global staff can see what courses errored on their dashboard
    staff_access = False
    errored_courses = {}
    if has_access(user, 'global', 'staff'):
        # Show any courses that errored on load
        staff_access = True
        errored_courses = modulestore().get_errored_courses()

    show_courseware_links_for = frozenset(course.id for course, _enrollment in course_enrollment_pairs
                                          if has_access(request.user, course, 'load'))

    course_modes = {course.id: complete_course_mode_info(course.id, enrollment) for course, enrollment in course_enrollment_pairs}
    cert_statuses = {course.id: cert_info(request.user, course) for course, _enrollment in course_enrollment_pairs}

    # only show email settings for Mongo course and when bulk email is turned on
    show_email_settings_for = frozenset(
        course.id for course, _enrollment in course_enrollment_pairs if (
            settings.FEATURES['ENABLE_INSTRUCTOR_EMAIL'] and
            modulestore().get_modulestore_type(course.id) == MONGO_MODULESTORE_TYPE and
            CourseAuthorization.instructor_email_enabled(course.id)
        )
    )

    # Verification Attempts
    verification_status, verification_msg = SoftwareSecurePhotoVerification.user_status(user)

    show_refund_option_for = frozenset(course.id for course, _enrollment in course_enrollment_pairs
                                       if _enrollment.refundable())

    # get info w.r.t ExternalAuthMap
    external_auth_map = None
    try:
        external_auth_map = ExternalAuthMap.objects.get(user=user)
    except ExternalAuthMap.DoesNotExist:
        pass

    context = {'course_enrollment_pairs': course_enrollment_pairs,
               'course_optouts': course_optouts,
               'message': message,
               'external_auth_map': external_auth_map,
               'staff_access': staff_access,
               'errored_courses': errored_courses,
               'show_courseware_links_for': show_courseware_links_for,
               'all_course_modes': course_modes,
               'cert_statuses': cert_statuses,
               'show_email_settings_for': show_email_settings_for,
               'verification_status': verification_status,
               'verification_msg': verification_msg,
               'show_refund_option_for': show_refund_option_for,
               }

    return render_to_response('dashboard.html', context)


def try_change_enrollment(request):
    """
    This method calls change_enrollment if the necessary POST
    parameters are present, but does not return anything. It
    simply logs the result or exception. This is usually
    called after a registration or login, as secondary action.
    It should not interrupt a successful registration or login.
    """
    if 'enrollment_action' in request.POST:
        try:
            enrollment_response = change_enrollment(request)
            # There isn't really a way to display the results to the user, so we just log it
            # We expect the enrollment to be a success, and will show up on the dashboard anyway
            log.info(
                "Attempted to automatically enroll after login. Response code: {0}; response body: {1}".format(
                    enrollment_response.status_code,
                    enrollment_response.content
                )
            )
            if enrollment_response.content != '':
                return enrollment_response.content
        except Exception, e:
            log.exception("Exception automatically enrolling after login: {0}".format(str(e)))


@require_POST
def change_enrollment(request):
    """
    Modify the enrollment status for the logged-in user.

    The request parameter must be a POST request (other methods return 405)
    that specifies course_id and enrollment_action parameters. If course_id or
    enrollment_action is not specified, if course_id is not valid, if
    enrollment_action is something other than "enroll" or "unenroll", if
    enrollment_action is "enroll" and enrollment is closed for the course, or
    if enrollment_action is "unenroll" and the user is not enrolled in the
    course, a 400 error will be returned. If the user is not logged in, 403
    will be returned; it is important that only this case return 403 so the
    front end can redirect the user to a registration or login page when this
    happens. This function should only be called from an AJAX request or
    as a post-login/registration helper, so the error messages in the responses
    should never actually be user-visible.
    """
    user = request.user

    action = request.POST.get("enrollment_action")
    course_id = request.POST.get("course_id")
    if course_id is None:
        return HttpResponseBadRequest(_("Course id not specified"))

    if not user.is_authenticated():
        return HttpResponseForbidden()

    if action == "enroll":
        # Make sure the course exists
        # We don't do this check on unenroll, or a bad course id can't be unenrolled from
        try:
            course = course_from_id(course_id)
        except ItemNotFoundError:
            log.warning("User {0} tried to enroll in non-existent course {1}"
                        .format(user.username, course_id))
            return HttpResponseBadRequest(_("Course id is invalid"))

        if not has_access(user, course, 'enroll'):
            return HttpResponseBadRequest(_("Enrollment is closed"))

        # If this course is available in multiple modes, redirect them to a page
        # where they can choose which mode they want.
        available_modes = CourseMode.modes_for_course(course_id)
        if len(available_modes) > 1:
            return HttpResponse(
                reverse("course_modes_choose", kwargs={'course_id': course_id})
            )

        current_mode = available_modes[0]

        org, course_num, run = course_id.split("/")
        dog_stats_api.increment(
            "common.student.enrollment",
            tags=["org:{0}".format(org),
                  "course:{0}".format(course_num),
                  "run:{0}".format(run)]
        )

        CourseEnrollment.enroll(user, course.id, mode=current_mode.slug)

        return HttpResponse()

    elif action == "add_to_cart":
        # Pass the request handling to shoppingcart.views
        # The view in shoppingcart.views performs error handling and logs different errors.  But this elif clause
        # is only used in the "auto-add after user reg/login" case, i.e. it's always wrapped in try_change_enrollment.
        # This means there's no good way to display error messages to the user.  So we log the errors and send
        # the user to the shopping cart page always, where they can reasonably discern the status of their cart,
        # whether things got added, etc

        shoppingcart.views.add_course_to_cart(request, course_id)
        return HttpResponse(
            reverse("shoppingcart.views.show_cart")
        )

    elif action == "unenroll":
        if not CourseEnrollment.is_enrolled(user, course_id):
            return HttpResponseBadRequest(_("You are not enrolled in this course"))
        CourseEnrollment.unenroll(user, course_id)
        org, course_num, run = course_id.split("/")
        dog_stats_api.increment(
            "common.student.unenrollment",
            tags=["org:{0}".format(org),
                  "course:{0}".format(course_num),
                  "run:{0}".format(run)]
        )
        return HttpResponse()
    else:
        return HttpResponseBadRequest(_("Enrollment action is invalid"))


def _parse_course_id_from_string(input_str):
    """
    Helper function to determine if input_str (typically the queryparam 'next') contains a course_id.
    @param input_str:
    @return: the course_id if found, None if not
    """
    m_obj = re.match(r'^/courses/(?P<course_id>[^/]+/[^/]+/[^/]+)', input_str)
    if m_obj:
        return m_obj.group('course_id')
    return None


def _get_course_enrollment_domain(course_id):
    """
    Helper function to get the enrollment domain set for a course with id course_id
    @param course_id:
    @return:
    """
    try:
        course = course_from_id(course_id)
        return course.enrollment_domain
    except ItemNotFoundError:
        return None


@ensure_csrf_cookie
def accounts_login(request):
    """
    This view is mainly used as the redirect from the @login_required decorator.  I don't believe that
    the login path linked from the homepage uses it.
    """
    if settings.FEATURES.get('AUTH_USE_CAS'):
        return redirect(reverse('cas-login'))
    if settings.FEATURES['AUTH_USE_MIT_CERTIFICATES']:
        # SSL login doesn't require a view, so redirect
        # to branding and allow that to process the login.
        return redirect(reverse('root'))
    # see if the "next" parameter has been set, whether it has a course context, and if so, whether
    # there is a course-specific place to redirect
    redirect_to = request.GET.get('next')
    if redirect_to:
        course_id = _parse_course_id_from_string(redirect_to)
        if course_id and _get_course_enrollment_domain(course_id):
            return external_auth.views.course_specific_login(request, course_id)

    context = {
        'platform_name': settings.PLATFORM_NAME,
    }
    return render_to_response('login.html', context)


# Need different levels of logging
@ensure_csrf_cookie
def login_user(request, error=""):
    """AJAX request to log in the user."""
    if 'email' not in request.POST or 'password' not in request.POST:
        return HttpResponse(json.dumps({'success': False,
                                        'value': _('There was an error receiving your login information. Please email us.')}))  # TODO: User error message

    email = request.POST['email']
    password = request.POST['password']
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        AUDIT_LOG.warning(u"Login failed - Unknown user email: {0}".format(email))
        user = None

    # check if the user has a linked shibboleth account, if so, redirect the user to shib-login
    # This behavior is pretty much like what gmail does for shibboleth.  Try entering some @stanford.edu
    # address into the Gmail login.
    if settings.FEATURES.get('AUTH_USE_SHIB') and user:
        try:
            eamap = ExternalAuthMap.objects.get(user=user)
            if eamap.external_domain.startswith(external_auth.views.SHIBBOLETH_DOMAIN_PREFIX):
                return HttpResponse(json.dumps({'success': False, 'redirect': reverse('shib-login')}))
        except ExternalAuthMap.DoesNotExist:
            # This is actually the common case, logging in user without external linked login
            AUDIT_LOG.info("User %s w/o external auth attempting login", user)

    # if the user doesn't exist, we want to set the username to an invalid
    # username so that authentication is guaranteed to fail and we can take
    # advantage of the ratelimited backend
    username = user.username if user else ""
    try:
        user = authenticate(username=username, password=password, request=request)
    # this occurs when there are too many attempts from the same IP address
    except RateLimitException:
        return HttpResponse(json.dumps({'success': False,
                                        'value': _('Too many failed login attempts. Try again later.')}))
    if user is None:
        # if we didn't find this username earlier, the account for this email
        # doesn't exist, and doesn't have a corresponding password
        if username != "":
            AUDIT_LOG.warning(u"Login failed - password for {0} is invalid".format(email))
        return HttpResponse(json.dumps({'success': False,
                                        'value': _('Email or password is incorrect.')}))

    if user is not None and user.is_active:
        try:
            # We do not log here, because we have a handler registered
            # to perform logging on successful logins.
            login(request, user)
            if request.POST.get('remember') == 'true':
                request.session.set_expiry(604800)
                log.debug("Setting user session to never expire")
            else:
                request.session.set_expiry(0)
        except Exception as e:
            AUDIT_LOG.critical("Login failed - Could not create session. Is memcached running?")
            log.critical("Login failed - Could not create session. Is memcached running?")
            log.exception(e)
            raise

        redirect_url = try_change_enrollment(request)

        dog_stats_api.increment("common.student.successful_login")
        response = HttpResponse(json.dumps({'success': True, 'redirect_url': redirect_url}))

        # set the login cookie for the edx marketing site
        # we want this cookie to be accessed via javascript
        # so httponly is set to None

        if request.session.get_expire_at_browser_close():
            max_age = None
            expires = None
        else:
            max_age = request.session.get_expiry_age()
            expires_time = time.time() + max_age
            expires = cookie_date(expires_time)

        response.set_cookie(settings.EDXMKTG_COOKIE_NAME,
                            'true', max_age=max_age,
                            expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                            path='/',
                            secure=None,
                            httponly=None)

        return response

    AUDIT_LOG.warning(u"Login failed - Account not active for user {0}, resending activation".format(username))

    reactivation_email_for_user(user)
    not_activated_msg = _("This account has not been activated. We have sent another activation message. Please check your e-mail for the activation instructions.")
    return HttpResponse(json.dumps({'success': False,
                                    'value': not_activated_msg}))


@ensure_csrf_cookie
def logout_user(request):
    """
    HTTP request to log out the user. Redirects to marketing page.
    Deletes both the CSRF and sessionid cookies so the marketing
    site can determine the logged in state of the user
    """
    # We do not log here, because we have a handler registered
    # to perform logging on successful logouts.
    logout(request)
    if settings.FEATURES.get('AUTH_USE_CAS'):
        target = reverse('cas-logout')
    else:
        target = '/'
    response = redirect(target)
    response.delete_cookie(settings.EDXMKTG_COOKIE_NAME,
                           path='/',
                           domain=settings.SESSION_COOKIE_DOMAIN)
    return response

@require_GET
@login_required
@ensure_csrf_cookie
def manage_user_standing(request):
    """
    Renders the view used to manage user standing. Also displays a table
    of user accounts that have been disabled and who disabled them.
    """
    if not request.user.is_staff:
        raise Http404
    all_disabled_accounts = UserStanding.objects.filter(
        account_status=UserStanding.ACCOUNT_DISABLED
    )

    all_disabled_users = [standing.user for standing in all_disabled_accounts]

    headers = ['username', 'account_changed_by']
    rows = []
    for user in all_disabled_users:
        row = [user.username, user.standing.all()[0].changed_by]
        rows.append(row)

    context = {'headers': headers, 'rows': rows}

    return render_to_response("manage_user_standing.html", context)


@require_POST
@login_required
@ensure_csrf_cookie
def disable_account_ajax(request):
    """
    Ajax call to change user standing. Endpoint of the form
    in manage_user_standing.html
    """
    if not request.user.is_staff:
        raise Http404
    username = request.POST.get('username')
    context = {}
    if username is None or username.strip() == '':
        context['message'] = _('Please enter a username')
        return JsonResponse(context, status=400)

    account_action = request.POST.get('account_action')
    if account_action is None:
        context['message'] = _('Please choose an option')
        return JsonResponse(context, status=400)

    username = username.strip()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        context['message'] = _("User with username {} does not exist").format(username)
        return JsonResponse(context, status=400)
    else:
        user_account, _success = UserStanding.objects.get_or_create(
            user=user, defaults={'changed_by': request.user},
        )
        if account_action == 'disable':
            user_account.account_status = UserStanding.ACCOUNT_DISABLED
            context['message'] = _("Successfully disabled {}'s account").format(username)
            log.info("{} disabled {}'s account".format(request.user, username))
        elif account_action == 'reenable':
            user_account.account_status = UserStanding.ACCOUNT_ENABLED
            context['message'] = _("Successfully reenabled {}'s account").format(username)
            log.info("{} reenabled {}'s account".format(request.user, username))
        else:
            context['message'] = _("Unexpected account status")
            return JsonResponse(context, status=400)
        user_account.changed_by = request.user
        user_account.standing_last_changed_at = datetime.datetime.now(UTC)
        user_account.save()

    return JsonResponse(context)


@login_required
@ensure_csrf_cookie
def change_setting(request):
    """JSON call to change a profile setting: Right now, location"""
    # TODO (vshnayder): location is no longer used
    up = UserProfile.objects.get(user=request.user)  # request.user.profile_cache
    if 'location' in request.POST:
        up.location = request.POST['location']
    up.save()

    return HttpResponse(json.dumps({'success': True,
                                    'location': up.location, }))


def _do_create_account(post_vars):
    """
    Given cleaned post variables, create the User and UserProfile objects, as well as the
    registration for this user.

    Returns a tuple (User, UserProfile, Registration).

    Note: this function is also used for creating test users.
    """
    user = User(username=post_vars['username'],
                email=post_vars['email'],
                is_active=False)
    user.set_password(post_vars['password'])
    registration = Registration()
    # TODO: Rearrange so that if part of the process fails, the whole process fails.
    # Right now, we can have e.g. no registration e-mail sent out and a zombie account
    try:
        user.save()
    except IntegrityError:
        js = {'success': False}
        # Figure out the cause of the integrity error
        if len(User.objects.filter(username=post_vars['username'])) > 0:
            js['value'] = _("An account with the Public Username '{username}' already exists.").format(username=post_vars['username'])
            js['field'] = 'username'
            return HttpResponse(json.dumps(js))

        if len(User.objects.filter(email=post_vars['email'])) > 0:
            js['value'] = _("An account with the Email '{email}' already exists.").format(email=post_vars['email'])
            js['field'] = 'email'
            return HttpResponse(json.dumps(js))

        raise

    registration.register(user)

    profile = UserProfile(user=user)
    profile.name = post_vars['name']
    profile.level_of_education = post_vars.get('level_of_education')
    profile.gender = post_vars.get('gender')
    profile.mailing_address = post_vars.get('mailing_address')
    profile.goals = post_vars.get('goals')

    try:
        profile.year_of_birth = int(post_vars['year_of_birth'])
    except (ValueError, KeyError):
        # If they give us garbage, just ignore it instead
        # of asking them to put an integer.
        profile.year_of_birth = None
    try:
        profile.save()
    except Exception:
        log.exception("UserProfile creation failed for user {id}.".format(id=user.id))
    return (user, profile, registration)


@ensure_csrf_cookie
def create_account(request, post_override=None):
    """
    JSON call to create new edX account.
    Used by form in signup_modal.html, which is included into navigation.html
    """
    js = {'success': False}

    post_vars = post_override if post_override else request.POST

    # if doing signup for an external authorization, then get email, password, name from the eamap
    # don't use the ones from the form, since the user could have hacked those
    # unless originally we didn't get a valid email or name from the external auth
    DoExternalAuth = 'ExternalAuthMap' in request.session
    if DoExternalAuth:
        eamap = request.session['ExternalAuthMap']
        try:
            validate_email(eamap.external_email)
            email = eamap.external_email
        except ValidationError:
            email = post_vars.get('email', '')
        if eamap.external_name.strip() == '':
            name = post_vars.get('name', '')
        else:
            name = eamap.external_name
        password = eamap.internal_password
        post_vars = dict(post_vars.items())
        post_vars.update(dict(email=email, name=name, password=password))
        log.debug(u'In create_account with external_auth: user = %s, email=%s', name, email)

    # Confirm we have a properly formed request
    for a in ['username', 'email', 'password', 'name']:
        if a not in post_vars:
            js['value'] = _("Error (401 {field}). E-mail us.").format(field=a)
            js['field'] = a
            return HttpResponse(json.dumps(js))

    if post_vars.get('honor_code', 'false') != u'true':
        js['value'] = _("To enroll, you must follow the honor code.").format(field=a)
        js['field'] = 'honor_code'
        return HttpResponse(json.dumps(js))

    # Can't have terms of service for certain SHIB users, like at Stanford
    tos_not_required = (settings.FEATURES.get("AUTH_USE_SHIB") and
                        settings.FEATURES.get('SHIB_DISABLE_TOS') and
                        DoExternalAuth and
                        eamap.external_domain.startswith(external_auth.views.SHIBBOLETH_DOMAIN_PREFIX))

    if not tos_not_required:
        if post_vars.get('terms_of_service', 'false') != u'true':
            js['value'] = _("You must accept the terms of service.").format(field=a)
            js['field'] = 'terms_of_service'
            return HttpResponse(json.dumps(js))

    # Confirm appropriate fields are there.
    # TODO: Check e-mail format is correct.
    # TODO: Confirm e-mail is not from a generic domain (mailinator, etc.)? Not sure if
    # this is a good idea
    # TODO: Check password is sane

    required_post_vars = ['username', 'email', 'name', 'password', 'terms_of_service', 'honor_code']
    if tos_not_required:
        required_post_vars = ['username', 'email', 'name', 'password', 'honor_code']

    for a in required_post_vars:
        if len(post_vars[a]) < 2:
            error_str = {'username': 'Username must be minimum of two characters long.',
                         'email': 'A properly formatted e-mail is required.',
                         'name': 'Your legal name must be a minimum of two characters long.',
                         'password': 'A valid password is required.',
                         'terms_of_service': 'Accepting Terms of Service is required.',
                         'honor_code': 'Agreeing to the Honor Code is required.'}
            js['value'] = error_str[a]
            js['field'] = a
            return HttpResponse(json.dumps(js))

    try:
        validate_email(post_vars['email'])
    except ValidationError:
        js['value'] = _("Valid e-mail is required.").format(field=a)
        js['field'] = 'email'
        return HttpResponse(json.dumps(js))

    try:
        validate_slug(post_vars['username'])
    except ValidationError:
        js['value'] = _("Username should only consist of A-Z and 0-9, with no spaces.").format(field=a)
        js['field'] = 'username'
        return HttpResponse(json.dumps(js))

    # Ok, looks like everything is legit.  Create the account.
    ret = _do_create_account(post_vars)
    if isinstance(ret, HttpResponse):  # if there was an error then return that
        return ret
    (user, profile, registration) = ret

    context = {
        'name': post_vars['name'],
        'key': registration.activation_key,
    }

    # composes activation email
    subject = render_to_string('emails/activation_email_subject.txt', context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/activation_email.txt', context)

    # don't send email if we are doing load testing or random user generation for some reason
    if not (settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING')):
        from_address = MicrositeConfiguration.get_microsite_configuration_value(
            'email_from_address',
            settings.DEFAULT_FROM_EMAIL
        )
        try:
            if settings.FEATURES.get('REROUTE_ACTIVATION_EMAIL'):
                dest_addr = settings.FEATURES['REROUTE_ACTIVATION_EMAIL']
                message = ("Activation for %s (%s): %s\n" % (user, user.email, profile.name) +
                           '-' * 80 + '\n\n' + message)
                send_mail(subject, message, from_address, [dest_addr], fail_silently=False)
            else:
                _res = user.email_user(subject, message, from_address)
        except:
            log.warning('Unable to send activation email to user', exc_info=True)
            js['value'] = _('Could not send activation e-mail.')
            return HttpResponse(json.dumps(js))

    # Immediately after a user creates an account, we log them in. They are only
    # logged in until they close the browser. They can't log in again until they click
    # the activation link from the email.
    login_user = authenticate(username=post_vars['username'], password=post_vars['password'])
    login(request, login_user)
    request.session.set_expiry(0)

    # TODO: there is no error checking here to see that the user actually logged in successfully,
    # and is not yet an active user.
    if login_user is not None:
        AUDIT_LOG.info(u"Login success on new account creation - {0}".format(login_user.username))

    if DoExternalAuth:
        eamap.user = login_user
        eamap.dtsignup = datetime.datetime.now(UTC)
        eamap.save()
        AUDIT_LOG.info("User registered with external_auth %s", post_vars['username'])
        AUDIT_LOG.info('Updated ExternalAuthMap for %s to be %s', post_vars['username'], eamap)

        if settings.FEATURES.get('BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH'):
            log.info('bypassing activation email')
            login_user.is_active = True
            login_user.save()
            AUDIT_LOG.info(u"Login activated on extauth account - {0} ({1})".format(login_user.username, login_user.email))

    redirect_url = try_change_enrollment(request)

    dog_stats_api.increment("common.student.account_created")

    response_params = {'success': True,
                       'redirect_url': redirect_url}

    response = HttpResponse(json.dumps(response_params))

    # set the login cookie for the edx marketing site
    # we want this cookie to be accessed via javascript
    # so httponly is set to None

    if request.session.get_expire_at_browser_close():
        max_age = None
        expires = None
    else:
        max_age = request.session.get_expiry_age()
        expires_time = time.time() + max_age
        expires = cookie_date(expires_time)

    response.set_cookie(settings.EDXMKTG_COOKIE_NAME,
                        'true', max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path='/',
                        secure=None,
                        httponly=None)
    return response


def auto_auth(request):
    """
    Create or configure a user account, then log in as that user.

    Enabled only when
    settings.FEATURES['AUTOMATIC_AUTH_FOR_TESTING'] is true.

    Accepts the following querystring parameters:
    * `username`, `email`, and `password` for the user account
    * `full_name` for the user profile (the user's full name; defaults to the username)
    * `staff`: Set to "true" to make the user global staff.
    * `course_id`: Enroll the student in the course with `course_id`

    If username, email, or password are not provided, use
    randomly generated credentials.
    """

    # Generate a unique name to use if none provided
    unique_name = uuid.uuid4().hex[0:30]

    # Use the params from the request, otherwise use these defaults
    username = request.GET.get('username', unique_name)
    password = request.GET.get('password', unique_name)
    email = request.GET.get('email', unique_name + "@example.com")
    full_name = request.GET.get('full_name', username)
    is_staff = request.GET.get('staff', None)
    course_id = request.GET.get('course_id', None)

    # Get or create the user object
    post_data = {
        'username': username,
        'email': email,
        'password': password,
        'name': full_name,
        'honor_code': u'true',
        'terms_of_service': u'true',
    }

    # Attempt to create the account.
    # If successful, this will return a tuple containing
    # the new user object; otherwise it will return an error
    # message.
    result = _do_create_account(post_data)

    if isinstance(result, tuple):
        user = result[0]

    # If we did not create a new account, the user might already
    # exist.  Attempt to retrieve it.
    else:
        user = User.objects.get(username=username)
        user.email = email
        user.set_password(password)
        user.save()

    # Set the user's global staff bit
    if is_staff is not None:
        user.is_staff = (is_staff == "true")
        user.save()

    # Activate the user
    reg = Registration.objects.get(user=user)
    reg.activate()
    reg.save()

    # Enroll the user in a course
    if course_id is not None:
        CourseEnrollment.enroll(user, course_id)

    # Log in as the user
    user = authenticate(username=username, password=password)
    login(request, user)

    # Provide the user with a valid CSRF token
    # then return a 200 response
    success_msg = u"Logged in user {0} ({1}) with password {2}".format(
        username, email, password
    )
    response = HttpResponse(success_msg)
    response.set_cookie('csrftoken', csrf(request)['csrf_token'])
    return response


@ensure_csrf_cookie
def activate_account(request, key):
    """When link in activation e-mail is clicked"""
    r = Registration.objects.filter(activation_key=key)
    if len(r) == 1:
        user_logged_in = request.user.is_authenticated()
        already_active = True
        if not r[0].user.is_active:
            r[0].activate()
            already_active = False

        # Enroll student in any pending courses he/she may have if auto_enroll flag is set
        student = User.objects.filter(id=r[0].user_id)
        if student:
            ceas = CourseEnrollmentAllowed.objects.filter(email=student[0].email)
            for cea in ceas:
                if cea.auto_enroll:
                    CourseEnrollment.enroll(student[0], cea.course_id)

        resp = render_to_response(
            "registration/activation_complete.html",
            {
                'user_logged_in': user_logged_in,
                'already_active': already_active
            }
        )
        return resp
    if len(r) == 0:
        return render_to_response(
            "registration/activation_invalid.html",
            {'csrf': csrf(request)['csrf_token']}
        )
    return HttpResponse(_("Unknown error. Please e-mail us to let us know how it happened."))


@ensure_csrf_cookie
def password_reset(request):
    """ Attempts to send a password reset e-mail. """
    if request.method != "POST":
        raise Http404

    form = PasswordResetFormNoActive(request.POST)
    if form.is_valid():
        form.save(use_https=request.is_secure(),
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  request=request,
                  domain_override=request.get_host())
    return HttpResponse(json.dumps({'success': True,
                                        'value': render_to_string('registration/password_reset_done.html', {})}))


def password_reset_confirm_wrapper(
    request,
    uidb36=None,
    token=None,
):
    """ A wrapper around django.contrib.auth.views.password_reset_confirm.
        Needed because we want to set the user as active at this step.
    """
    # cribbed from django.contrib.auth.views.password_reset_confirm
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
        user.is_active = True
        user.save()
    except (ValueError, User.DoesNotExist):
        pass
    # we also want to pass settings.PLATFORM_NAME in as extra_context

    extra_context = {"platform_name": settings.PLATFORM_NAME}
    return password_reset_confirm(
        request, uidb36=uidb36, token=token, extra_context=extra_context
    )


def reactivation_email_for_user(user):
    try:
        reg = Registration.objects.get(user=user)
    except Registration.DoesNotExist:
        return HttpResponse(json.dumps({'success': False,
                                        'error': _('No inactive user with this e-mail exists')}))

    d = {'name': user.profile.name,
         'key': reg.activation_key}

    subject = render_to_string('emails/activation_email_subject.txt', d)
    subject = ''.join(subject.splitlines())
    message = render_to_string('emails/activation_email.txt', d)

    try:
        _res = user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
    except:
        log.warning('Unable to send reactivation email', exc_info=True)
        return HttpResponse(json.dumps({'success': False, 'error': _('Unable to send reactivation email')}))

    return HttpResponse(json.dumps({'success': True}))


@ensure_csrf_cookie
def change_email_request(request):
    """ AJAX call from the profile page. User wants a new e-mail.
    """
    ## Make sure it checks for existing e-mail conflicts
    if not request.user.is_authenticated:
        raise Http404

    user = request.user

    if not user.check_password(request.POST['password']):
        return HttpResponse(json.dumps({'success': False,
                                        'error': _('Invalid password')}))

    new_email = request.POST['new_email']
    try:
        validate_email(new_email)
    except ValidationError:
        return HttpResponse(json.dumps({'success': False,
                                        'error': _('Valid e-mail address required.')}))

    if User.objects.filter(email=new_email).count() != 0:
        ## CRITICAL TODO: Handle case sensitivity for e-mails
        return HttpResponse(json.dumps({'success': False,
                                        'error': _('An account with this e-mail already exists.')}))

    pec_list = PendingEmailChange.objects.filter(user=request.user)
    if len(pec_list) == 0:
        pec = PendingEmailChange()
        pec.user = user
    else:
        pec = pec_list[0]

    pec.new_email = request.POST['new_email']
    pec.activation_key = uuid.uuid4().hex
    pec.save()

    if pec.new_email == user.email:
        pec.delete()
        return HttpResponse(json.dumps({'success': False,
                                        'error': _('Old email is the same as the new email.')}))

    context = {
        'key': pec.activation_key,
        'old_email': user.email,
        'new_email': pec.new_email
    }

    subject = render_to_string('emails/email_change_subject.txt', context)
    subject = ''.join(subject.splitlines())

    message = render_to_string('emails/email_change.txt', context)

    from_address = MicrositeConfiguration.get_microsite_configuration_value(
        'email_from_address',
        settings.DEFAULT_FROM_EMAIL
    )

    _res = send_mail(subject, message, from_address, [pec.new_email])

    return HttpResponse(json.dumps({'success': True}))


@ensure_csrf_cookie
@transaction.commit_manually
def confirm_email_change(request, key):
    """ User requested a new e-mail. This is called when the activation
    link is clicked. We confirm with the old e-mail, and update
    """
    try:
        try:
            pec = PendingEmailChange.objects.get(activation_key=key)
        except PendingEmailChange.DoesNotExist:
            response = render_to_response("invalid_email_key.html", {})
            transaction.rollback()
            return response

        user = pec.user
        address_context = {
            'old_email': user.email,
            'new_email': pec.new_email
        }

        if len(User.objects.filter(email=pec.new_email)) != 0:
            response = render_to_response("email_exists.html", {})
            transaction.rollback()
            return response

        subject = render_to_string('emails/email_change_subject.txt', address_context)
        subject = ''.join(subject.splitlines())
        message = render_to_string('emails/confirm_email_change.txt', address_context)
        up = UserProfile.objects.get(user=user)
        meta = up.get_meta()
        if 'old_emails' not in meta:
            meta['old_emails'] = []
        meta['old_emails'].append([user.email, datetime.datetime.now(UTC).isoformat()])
        up.set_meta(meta)
        up.save()
        # Send it to the old email...
        try:
            user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
        except Exception:
            log.warning('Unable to send confirmation email to old address', exc_info=True)
            response = render_to_response("email_change_failed.html", {'email': user.email})
            transaction.rollback()
            return response

        user.email = pec.new_email
        user.save()
        pec.delete()
        # And send it to the new email...
        try:
            user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
        except Exception:
            log.warning('Unable to send confirmation email to new address', exc_info=True)
            response = render_to_response("email_change_failed.html", {'email': pec.new_email})
            transaction.rollback()
            return response

        response = render_to_response("email_change_successful.html", address_context)
        transaction.commit()
        return response
    except Exception:
        # If we get an unexpected exception, be sure to rollback the transaction
        transaction.rollback()
        raise


@ensure_csrf_cookie
def change_name_request(request):
    """ Log a request for a new name. """
    if not request.user.is_authenticated:
        raise Http404

    try:
        pnc = PendingNameChange.objects.get(user=request.user)
    except PendingNameChange.DoesNotExist:
        pnc = PendingNameChange()
    pnc.user = request.user
    pnc.new_name = request.POST['new_name']
    pnc.rationale = request.POST['rationale']
    if len(pnc.new_name) < 2:
        return HttpResponse(json.dumps({'success': False, 'error': _('Name required')}))
    pnc.save()

    # The following automatically accepts name change requests. Remove this to
    # go back to the old system where it gets queued up for admin approval.
    accept_name_change_by_id(pnc.id)

    return HttpResponse(json.dumps({'success': True}))


@ensure_csrf_cookie
def pending_name_changes(request):
    """ Web page which allows staff to approve or reject name changes. """
    if not request.user.is_staff:
        raise Http404

    changes = list(PendingNameChange.objects.all())
    js = {'students': [{'new_name': c.new_name,
                        'rationale': c.rationale,
                        'old_name': UserProfile.objects.get(user=c.user).name,
                        'email': c.user.email,
                        'uid': c.user.id,
                        'cid': c.id} for c in changes]}
    return render_to_response('name_changes.html', js)


@ensure_csrf_cookie
def reject_name_change(request):
    """ JSON: Name change process. Course staff clicks 'reject' on a given name change """
    if not request.user.is_staff:
        raise Http404

    try:
        pnc = PendingNameChange.objects.get(id=int(request.POST['id']))
    except PendingNameChange.DoesNotExist:
        return HttpResponse(json.dumps({'success': False, 'error': _('Invalid ID')}))

    pnc.delete()
    return HttpResponse(json.dumps({'success': True}))


def accept_name_change_by_id(id):
    try:
        pnc = PendingNameChange.objects.get(id=id)
    except PendingNameChange.DoesNotExist:
        return HttpResponse(json.dumps({'success': False, 'error': _('Invalid ID')}))

    u = pnc.user
    up = UserProfile.objects.get(user=u)

    # Save old name
    meta = up.get_meta()
    if 'old_names' not in meta:
        meta['old_names'] = []
    meta['old_names'].append([up.name, pnc.rationale, datetime.datetime.now(UTC).isoformat()])
    up.set_meta(meta)

    up.name = pnc.new_name
    up.save()
    pnc.delete()

    return HttpResponse(json.dumps({'success': True}))


@ensure_csrf_cookie
def accept_name_change(request):
    """ JSON: Name change process. Course staff clicks 'accept' on a given name change

    We used this during the prototype but now we simply record name changes instead
    of manually approving them. Still keeping this around in case we want to go
    back to this approval method.
    """
    if not request.user.is_staff:
        raise Http404

    return accept_name_change_by_id(int(request.POST['id']))


@require_POST
@login_required
@ensure_csrf_cookie
def change_email_settings(request):
    """Modify logged-in user's setting for receiving emails from a course."""
    user = request.user

    course_id = request.POST.get("course_id")
    receive_emails = request.POST.get("receive_emails")
    if receive_emails:
        optout_object = Optout.objects.filter(user=user, course_id=course_id)
        if optout_object:
            optout_object.delete()
        log.info(u"User {0} ({1}) opted in to receive emails from course {2}".format(user.username, user.email, course_id))
        track.views.server_track(request, "change-email-settings", {"receive_emails": "yes", "course": course_id}, page='dashboard')
    else:
        Optout.objects.get_or_create(user=user, course_id=course_id)
        log.info(u"User {0} ({1}) opted out of receiving emails from course {2}".format(user.username, user.email, course_id))
        track.views.server_track(request, "change-email-settings", {"receive_emails": "no", "course": course_id}, page='dashboard')

    return HttpResponse(json.dumps({'success': True}))

from student.firebase_token_generator import create_token


@login_required
def token(request):
    '''
    Return a token for the backend of annotations.
    It uses the course id to retrieve a variable that contains the secret
    token found in inheritance.py. It also contains information of when
    the token was issued. This will be stored with the user along with
    the id for identification purposes in the backend.
    '''
    course_id = request.GET.get("course_id")
    course = course_from_id(course_id)
    dtnow = datetime.datetime.now()
    dtutcnow = datetime.datetime.utcnow()
    delta = dtnow - dtutcnow
    newhour, newmin = divmod((delta.days * 24 * 60 * 60 + delta.seconds + 30) // 60, 60)
    newtime = "%s%+02d:%02d" % (dtnow.isoformat(), newhour, newmin)
    secret = course.annotation_token_secret
    custom_data = {"issuedAt": newtime, "consumerKey": secret, "userId": request.user.email, "ttl": 86400}
    newtoken = create_token(secret, custom_data)
    response = HttpResponse(newtoken, mimetype="text/plain")
    return response
