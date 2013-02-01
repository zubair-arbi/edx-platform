#########################################################################################
#copy of all imports in views.py

from util.json_request import expect_json
import json
import logging
import os
import sys
import time
import tarfile
import shutil
from datetime import datetime
from collections import defaultdict
from uuid import uuid4
from path import path
from xmodule.modulestore.xml_exporter import export_to_xml
from tempfile import mkdtemp
from django.core.servers.basehttp import FileWrapper
from django.core.files.temp import NamedTemporaryFile

# to install PIL on MacOSX: 'easy_install http://dist.repoze.org/PIL-1.1.6.tar.gz'
from PIL import Image

from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.context_processors import csrf
from django_future.csrf import ensure_csrf_cookie
from django.core.urlresolvers import reverse
from django.conf import settings

from xmodule.modulestore import Location
from xmodule.modulestore.exceptions import ItemNotFoundError, InvalidLocationError
from xmodule.x_module import ModuleSystem
from xmodule.error_module import ErrorDescriptor
from xmodule.errortracker import exc_info_to_str
from static_replace import replace_urls
from external_auth.views import ssl_login_shortcut

from mitxmako.shortcuts import render_to_response, render_to_string
from xmodule.modulestore.django import modulestore
from xmodule_modifiers import replace_static_urls, wrap_xmodule
from xmodule.exceptions import NotFoundError
from functools import partial

from xmodule.contentstore.django import contentstore
from xmodule.contentstore.content import StaticContent

from auth.authz import is_user_in_course_group_role, get_users_in_course_group_by_role
from auth.authz import get_user_by_email, add_user_to_course_group, remove_user_from_course_group
from auth.authz import INSTRUCTOR_ROLE_NAME, STAFF_ROLE_NAME, create_all_course_groups
from .utils import get_course_location_for_item, get_lms_link_for_item, compute_unit_state, get_date_display, UnitState, get_course_for_item

from xmodule.modulestore.xml_importer import import_from_xml
from contentstore.course_info_model import get_course_updates,\
    update_course_updates, delete_course_update
from cache_toolbox.core import del_cached_content
from xmodule.timeparse import stringify_time
from contentstore.module_info_model import get_module_info, set_module_info
from cms.djangoapps.models.settings.course_details import CourseDetails,\
    CourseSettingsEncoder
from cms.djangoapps.models.settings.course_grading import CourseGradingModel
from cms.djangoapps.contentstore.utils import get_modulestore
from lxml import etree

#########################################################################################
import contentstore.views as views

from django.test import TestCase
from mock import MagicMock

import factories

#########################################################################################
#it is possible some of this tests are broken. When I run them I get error messages I 
#have not understood but which are unrelated to the code below. So it has to do with
#either the import statementes or setting up configuring mongod on my computer.

class StaticPagesTest(TestCase):

    def setUp(self):
        
        self.user = UserFactory()
        self.request = MagicMock()
        self.org = MagicMock()
        self.course = CourseFactory()
        self.coursename = MagicMock()
        self.request.user = self.user
        
        self.request1 = MagicMock()
        self.user1 = UserFactory(is_authenticated = True, is_staff = True)
        self.request1.user = self.user1
 
    def test_static_pages(self):

        self.assertRaises(PermissionDenied, views.static_pages, self.request, self.org, 
                          self.course, self.coursename)

        self.assertEqual(views.static_pages(self.request1, self.org, self.course, self.coursename), 
                         render_to_response('static-pages.html', 
                                            {'active_tab': 'pages', 'context_course': self.course})

#########################################################################################

class UserAuthorStringTest(TestCase):

    def setUp(self):

        self.user = MagicMock()
        self.user.first_name = 'Lyle'
        self.user.last_name = 'Jenkins'
        self.user.email = 'lyle@edx.org'

        self.user0 = MagicMock()
        self.user0.first_name = ''
        self.user0.last_name = ''
        self.user0.username - 'lyle'
        self.user0.email = 'lyle@mit.edu'
        
    def test_user_author_string(self):

        self.assertEqual(views.user_author_string(self.user), 'Lyle Jenkins <lyle@edx.org>')

        self.assertEqual(views.user_author_string(self.user0), 'lyle <lyle@edx.org>')

#########################################################################################
        

        
















    
