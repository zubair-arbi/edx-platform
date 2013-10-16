"""
A command to revert any "/static/.." paths in public HTML content to the fully qualified
path "c4x:/org/number/asset/.....
"""

import re

from django.core.management.base import BaseCommand
from xmodule.course_module import CourseDescriptor
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError


class Command(BaseCommand):
    """
    revert_static_paths command
    """

    help = "Reverts '/static' paths for existing public html modules to their original full path.\n"
    help += "Draft items are unaffected by this command."
    help += "You can use this if you find that the automatic parser, on export/import or clone_course, \n"
    help += "unintentionally did some bad things to your html\n"
    help += "Usage: revert_static_paths course_id\n"
    help += "   course_id: course's ID, such as Medicine/HRP258/Statistics_in_Medicine\n"

    def handle(self, *args, **options):

        if len(args) > 0:
            course_id = args[0]
        else:
            print self.help
            return

        draft_mstore = modulestore()
        live_mstore = modulestore('direct')
        pre_string = '/static'
        org, course, name = course_id.split('/')

        post_string = '/c4x/' + org + '/' + course + '/asset'

        # Traverse the draft modulestore for locations of html type problems
        html_problems = get_list_html_problems(draft_mstore, course_id)
        if html_problems:
            # Substitute the string for the 'live' modulestore instance
            do_substitution(live_mstore, html_problems, pre_string, post_string)


def get_list_html_problems(mstore, course_id):
    """
    
    """

    course = mstore.get_instance(course_id, CourseDescriptor.id_to_location(course_id), depth=4)

    for section in course.get_children():
        for subsection in section.get_children():

            html_problems = []
            for unit in subsection.get_children():
                for child in unit.get_children():
                    if child.location.category == 'html':
                        html_problems.append(child)

    return html_problems


def do_substitution(mstore, html_problems, pre_string, post_string):
    """
    
    """

    for html_problem in html_problems:
        try:
            public_problem = mstore.get_item(html_problem.location, 0)
        except ItemNotFoundError:
            print "No public item found for", html_problem.location, "...skipping"
            continue

        data = public_problem.data
        replaced_data = re.sub(pre_string, post_string, data)
        mstore.update_item(public_problem.location, replaced_data)
        print "Modifying item", public_problem.location
