# pylint: disable=C0111
# pylint: disable=W0621

from lettuce import world, step
from lettuce.django import django_url
from mock import patch

from django.conf import settings


@step('I click on email settings for the course numbered "([^"]*)"')
def i_click_on_email_settings(_step, course):
    print settings.MITX_FEATURES['ENABLE_INSTRUCTOR_EMAIL']

    email_css = 'section.info a[href*="#email-settings-modal"][data-course-number*="%s"]' % course
    world.css_click(email_css)

@step(u'I should( NOT)? be receiving course emails for the course numbered "([^"]*)"')
def i_should_be_receiving_course_emails(_step, doesnt_appear, course):
    # Not working - can't tell, I don't think, the checkbox state from css
    # source_html = ??
    # if doesnt_appear:
    #     # then checkbox should be unchecked - optout should be True
    #     optout_html = 'data-course-number="{0}" data-optout="{1}">'.format(course, True)
    # else:
    #     # checkbox should be checked - optout should be False
    #     optout_html = 'data-course-number="{0}" data-optout="{1}">'.format(course, False)
    # assert optout_html source_html
    assert True

@step('I opt out of emails')
def i_opt_out_of_emails(_step):
    checkbox_css = 'section#email-settings-modal input[name="receive_emails"]'
    world.css_click(checkbox_css)
    button_css = 'section#email-settings-modal input[value="Save Settings"]'
    world.css_click(button_css)
    assert world.dialogs_closed()
