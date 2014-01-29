# Compute grades using real division, with no integer truncation
from __future__ import division
from collections import defaultdict
import json
import random
import logging

from contextlib import contextmanager
from django.conf import settings
from django.db import transaction
from django.test.client import RequestFactory

from dogapi import dog_stats_api

from courseware import courses
from courseware.model_data import FieldDataCache
from xmodule import graders
from xmodule.graders import Score
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.util.duedate import get_extended_due_date
from .models import StudentModule
from .module_render import get_module_for_descriptor

log = logging.getLogger("edx.courseware")


def yield_dynamic_descriptor_descendents(descriptor, module_creator):
    """
    This returns all of the descendants of a descriptor. If the descriptor
    has dynamic children, the module will be created using module_creator
    and the children (as descriptors) of that module will be returned.
    """
    def get_dynamic_descriptor_children(descriptor):
        if descriptor.has_dynamic_children():
            module = module_creator(descriptor)
            if module is None:
                return []
            return module.get_child_descriptors()
        else:
            return descriptor.get_children()

    stack = [descriptor]

    while len(stack) > 0:
        next_descriptor = stack.pop()
        stack.extend(get_dynamic_descriptor_children(next_descriptor))
        yield next_descriptor


def answer_distributions(course_id):
    """
    Given a course_id, return answer distributions in the form of a dictionary
    mapping:

      (problem url_name, problem display_name, problem_id) -> {dict: answer -> count}

    Answer distributions are found by iterating through all StudentModule
    entries for a given course with type="problem" and a grade that is not null.
    This means that we only count LoncapaProblems that people have submitted.
    Other types of items like ORA or sequences will not be collected. Empty
    Loncapa problem state that gets created from runnig the progress page is
    also not counted.

    This method accesses the StudentModule table directly instead of using the
    CapaModule abstraction. The main reason for this is so that we can generate
    the report without any side-effects -- we don't have to worry about answer
    distribution potentially causing re-evaluation of the student answer. This
    also allows us to use the read-replica database, which reduces risk of bad
    locking behavior. And quite frankly, it makes this a lot less confusing.

    Also, we're pulling all available records from the database for this course
    rather than crawling through a student's course-tree -- the latter could
    potentially cause us trouble with A/B testing. The distribution report may
    not be aware of problems that are not visible to the user being used to
    generate the report.

    This method will try to use a read-replica database if one is available.
    """
    # dict: { module.module_state_key : (url_name, display_name) }
    state_keys_to_problem_info = {}  # For caching, used by url_and_display_name

    def url_and_display_name(module_state_key):
        """
        For a given module_state_key, return the problem's url and display_name.
        Handle modulestore access and caching. This method ignores permissions.
        May throw an ItemNotFoundError if there is no content that corresponds
        to this module_state_key.
        """
        problem_store = modulestore()
        if module_state_key not in state_keys_to_problem_info:
            problems = problem_store.get_items(module_state_key, course_id=course_id, depth=1)
            if not problems:
                # Likely means that the problem was deleted from the course
                # after the student had answered. We log this suspicion where
                # this exception is caught.
                raise ItemNotFoundError(
                    "Answer Distribution: Module {} not found for course {}"
                    .format(module_state_key, course_id)
                )
            problem = problems[0]
            problem_info = (problem.url_name, problem.display_name_with_default)
            state_keys_to_problem_info[module_state_key] = problem_info

        return state_keys_to_problem_info[module_state_key]

    # Iterate through all problems submitted for this course in no particular
    # order, and build up our answer_counts dict that we will eventually return
    answer_counts = defaultdict(lambda: defaultdict(int))
    for module in StudentModule.all_submitted_problems_read_only(course_id):
        try:
            state_dict = json.loads(module.state) if module.state else {}
            raw_answers = state_dict.get("student_answers", {})
        except ValueError:
            log.error(
                "Answer Distribution: Could not parse module state for " +
                "StudentModule id={}, course={}".format(module.id, course_id)
            )
            continue

        # Each problem part has an ID that is derived from the
        # module.module_state_key (with some suffix appended)
        for problem_part_id, raw_answer in raw_answers.items():
            # Convert whatever raw answers we have (numbers, unicode, None, etc.)
            # to be unicode values. Note that if we get a string, it's always
            # unicode and not str -- state comes from the json decoder, and that
            # always returns unicode for strings.
            answer = unicode(raw_answer)

            try:
                url, display_name = url_and_display_name(module.module_state_key)
            except ItemNotFoundError:
                msg = "Answer Distribution: Item {} referenced in StudentModule {} " + \
                      "for user {} in course {} not found; " + \
                      "This can happen if a student answered a question that " + \
                      "was later deleted from the course. This answer will be " + \
                      "omitted from the answer distribution CSV."
                log.warning(
                    msg.format(module.module_state_key, module.id, module.student_id, course_id)
                )
                continue

            answer_counts[(url, display_name, problem_part_id)][answer] += 1

    return answer_counts

@transaction.commit_manually
def grade(student, request, course, keep_raw_scores=False):
    """
    Wraps "_grade" with the manual_transaction context manager just in case
    there are unanticipated errors.
    """
    with manual_transaction():
        return _grade(student, request, course, keep_raw_scores)


def _grade(student, request, course, keep_raw_scores):
    """
    Unwrapped version of "grade"

    This grades a student as quickly as possible. It returns the
    output from the course grader, augmented with the final letter
    grade. The keys in the output are:

    course: a CourseDescriptor

    - grade : A final letter grade.
    - percent : The final percent for the class (rounded up).
    - section_breakdown : A breakdown of each section that makes
      up the grade. (For display)
    - grade_breakdown : A breakdown of the major components that
      make up the final grade. (For display)
    - keep_raw_scores : if True, then value for key 'raw_scores' contains scores
      for every graded module

    More information on the format is in the docstring for CourseGrader.
    """
    grading_context = course.grading_context
    raw_scores = []

    totaled_scores = {}
    # This next complicated loop is just to collect the totaled_scores, which is
    # passed to the grader
    for section_format, sections in grading_context['graded_sections'].iteritems():
        format_scores = []
        for section in sections:
            section_descriptor = section['section_descriptor']
            section_name = section_descriptor.display_name_with_default

            # some problems have state that is updated independently of interaction
            # with the LMS, so they need to always be scored. (E.g. foldit.,
            # combinedopenended)
            should_grade_section = any(
                descriptor.always_recalculate_grades for descriptor in section['xmoduledescriptors']
            )

            # If we haven't seen a single problem in the section, we don't have to grade it at all! We can assume 0%
            if not should_grade_section:
                with manual_transaction():
                    should_grade_section = StudentModule.objects.filter(
                        student=student,
                        module_state_key__in=[
                            descriptor.location for descriptor in section['xmoduledescriptors']
                        ]
                    ).exists()

            if should_grade_section:
                scores = []

                def create_module(descriptor):
                    '''creates an XModule instance given a descriptor'''
                    # TODO: We need the request to pass into here. If we could forego that, our arguments
                    # would be simpler
                    with manual_transaction():
                        field_data_cache = FieldDataCache([descriptor], course.id, student)
                    return get_module_for_descriptor(student, request, descriptor, field_data_cache, course.id)

                for module_descriptor in yield_dynamic_descriptor_descendents(section_descriptor, create_module):

                    (correct, total) = get_score(course.id, student, module_descriptor, create_module)
                    if correct is None and total is None:
                        continue

                    if settings.GENERATE_PROFILE_SCORES:  	# for debugging!
                        if total > 1:
                            correct = random.randrange(max(total - 2, 1), total + 1)
                        else:
                            correct = total

                    graded = module_descriptor.graded
                    if not total > 0:
                        #We simply cannot grade a problem that is 12/0, because we might need it as a percentage
                        graded = False

                    scores.append(Score(correct, total, graded, module_descriptor.display_name_with_default))

                _, graded_total = graders.aggregate_scores(scores, section_name)
                if keep_raw_scores:
                    raw_scores += scores
            else:
                graded_total = Score(0.0, 1.0, True, section_name)

            #Add the graded total to totaled_scores
            if graded_total.possible > 0:
                format_scores.append(graded_total)
            else:
                log.exception("Unable to grade a section with a total possible score of zero. " +
                              str(section_descriptor.location))

        totaled_scores[section_format] = format_scores

    grade_summary = course.grader.grade(totaled_scores, generate_random_scores=settings.GENERATE_PROFILE_SCORES)

    # We round the grade here, to make sure that the grade is an whole percentage and
    # doesn't get displayed differently than it gets grades
    grade_summary['percent'] = round(grade_summary['percent'] * 100 + 0.05) / 100

    letter_grade = grade_for_percentage(course.grade_cutoffs, grade_summary['percent'])
    grade_summary['grade'] = letter_grade
    grade_summary['totaled_scores'] = totaled_scores  	# make this available, eg for instructor download & debugging
    if keep_raw_scores:
        grade_summary['raw_scores'] = raw_scores        # way to get all RAW scores out to instructor
                                                        # so grader can be double-checked
    return grade_summary


def grade_for_percentage(grade_cutoffs, percentage):
    """
    Returns a letter grade as defined in grading_policy (e.g. 'A' 'B' 'C' for 6.002x) or None.

    Arguments
    - grade_cutoffs is a dictionary mapping a grade to the lowest
        possible percentage to earn that grade.
    - percentage is the final percent across all problems in a course
    """

    letter_grade = None

    # Possible grades, sorted in descending order of score
    descending_grades = sorted(grade_cutoffs, key=lambda x: grade_cutoffs[x], reverse=True)
    for possible_grade in descending_grades:
        if percentage >= grade_cutoffs[possible_grade]:
            letter_grade = possible_grade
            break

    return letter_grade


@transaction.commit_manually
def progress_summary(student, request, course):
    """
    Wraps "_progress_summary" with the manual_transaction context manager just
    in case there are unanticipated errors.
    """
    with manual_transaction():
        return _progress_summary(student, request, course)


# TODO: This method is not very good. It was written in the old course style and
# then converted over and performance is not good. Once the progress page is redesigned
# to not have the progress summary this method should be deleted (so it won't be copied).
def _progress_summary(student, request, course):
    """
    Unwrapped version of "progress_summary".

    This pulls a summary of all problems in the course.

    Returns
    - courseware_summary is a summary of all sections with problems in the course.
    It is organized as an array of chapters, each containing an array of sections,
    each containing an array of scores. This contains information for graded and
    ungraded problems, and is good for displaying a course summary with due dates,
    etc.

    Arguments:
        student: A User object for the student to grade
        course: A Descriptor containing the course to grade

    If the student does not have access to load the course module, this function
    will return None.

    """
    with manual_transaction():
        field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
            course.id, student, course, depth=None
        )
        # TODO: We need the request to pass into here. If we could
        # forego that, our arguments would be simpler
        course_module = get_module_for_descriptor(student, request, course, field_data_cache, course.id)
        if not course_module:
            # This student must not have access to the course.
            return None

    chapters = []
    # Don't include chapters that aren't displayable (e.g. due to error)
    for chapter_module in course_module.get_display_items():
        # Skip if the chapter is hidden
        if chapter_module.hide_from_toc:
            continue

        sections = []

        for section_module in chapter_module.get_display_items():
            # Skip if the section is hidden
            with manual_transaction():
                if section_module.hide_from_toc:
                    continue

                graded = section_module.graded
                scores = []

                module_creator = section_module.xmodule_runtime.get_module

                for module_descriptor in yield_dynamic_descriptor_descendents(section_module, module_creator):
                    course_id = course.id
                    (correct, total) = get_score(course_id, student, module_descriptor, module_creator)
                    if correct is None and total is None:
                        continue

                    scores.append(Score(correct, total, graded, module_descriptor.display_name_with_default))

                scores.reverse()
                section_total, _ = graders.aggregate_scores(
                    scores, section_module.display_name_with_default)

                module_format = section_module.format if section_module.format is not None else ''
                sections.append({
                    'display_name': section_module.display_name_with_default,
                    'url_name': section_module.url_name,
                    'scores': scores,
                    'section_total': section_total,
                    'format': module_format,
                    'due': get_extended_due_date(section_module),
                    'graded': graded,
                })

        chapters.append({
            'course': course.display_name_with_default,
            'display_name': chapter_module.display_name_with_default,
            'url_name': chapter_module.url_name,
            'sections': sections
        })

    return chapters

def get_score(course_id, user, problem_descriptor, module_creator):
    """
    Return the score for a user on a problem, as a tuple (correct, total).
    e.g. (5,7) if you got 5 out of 7 points.

    If this problem doesn't have a score, or we couldn't load it, returns (None,
    None).

    user: a Student object
    problem_descriptor: an XModuleDescriptor
    module_creator: a function that takes a descriptor, and returns the corresponding XModule for this user.
           Can return None if user doesn't have access, or if something else went wrong.
    cache: A FieldDataCache
    """
    if not user.is_authenticated():
        return (None, None)

    # some problems have state that is updated independently of interaction
    # with the LMS, so they need to always be scored. (E.g. foldit.)
    if problem_descriptor.always_recalculate_grades:
        problem = module_creator(problem_descriptor)
        if problem is None:
            return (None, None)
        score = problem.get_score()
        if score is not None:
            return (score['score'], score['total'])
        else:
            return (None, None)

    if not problem_descriptor.has_score:
        # These are not problems, and do not have a score
        return (None, None)

    try:
        student_module = StudentModule.objects.get(
            student=user,
            course_id=course_id,
            module_state_key=problem_descriptor.location
        )
    except StudentModule.DoesNotExist:
        student_module = None

    if student_module is not None and student_module.max_grade is not None:
        correct = student_module.grade if student_module.grade is not None else 0
        total = student_module.max_grade
    else:
        # If the problem was not in the cache, or hasn't been graded yet,
        # we need to instantiate the problem.
        # Otherwise, the max score (cached in student_module) won't be available
        problem = module_creator(problem_descriptor)
        if problem is None:
            return (None, None)

        correct = 0.0
        total = problem.max_score()

        # Problem may be an error module (if something in the problem builder failed)
        # In which case total might be None
        if total is None:
            return (None, None)

    # Now we re-weight the problem, if specified
    weight = problem_descriptor.weight
    if weight is not None:
        if total == 0:
            log.exception("Cannot reweight a problem with zero total points. Problem: " + str(student_module))
            return (correct, total)
        correct = correct * weight / total
        total = weight

    return (correct, total)


@contextmanager
def manual_transaction():
    """A context manager for managing manual transactions"""
    try:
        yield
    except Exception:
        transaction.rollback()
        log.exception('Due to an error, this transaction has been rolled back')
        raise
    else:
        transaction.commit()


def iterate_grades_for(course_id, students):
    """Given a course_id and an iterable of students (User), yield a tuple of:

    (student, gradeset, err_msg) for every student enrolled in the course.

    If an error occurred, gradeset will be an empty dict and err_msg will be an
    exception message. If there was no error, err_msg is an empty string.

    The gradeset is a dictionary with the following fields:

    - grade : A final letter grade.
    - percent : The final percent for the class (rounded up).
    - section_breakdown : A breakdown of each section that makes
        up the grade. (For display)
    - grade_breakdown : A breakdown of the major components that
        make up the final grade. (For display)
    - raw_scores: contains scores for every graded module
    """
    course = courses.get_course_by_id(course_id)

    # We make a fake request because grading code expects to be able to look at
    # the request. We have to attach the correct user to the request before
    # grading that student.
    request = RequestFactory().get('/')

    for student in students:
        with dog_stats_api.timer('lms.grades.iterate_grades_for', tags=['action:{}'.format(course_id)]):
            try:
                request.user = student
                # Grading calls problem rendering, which calls masquerading,
                # which checks session vars -- thus the empty session dict below.
                # It's not pretty, but untangling that is currently beyond the
                # scope of this feature.
                request.session = {}
                gradeset = grade(student, request, course)
                yield student, gradeset, ""
            except Exception as exc:  # pylint: disable=broad-except
                # Keep marching on even if this student couldn't be graded for
                # some reason, but log it for future reference.
                log.exception(
                    'Cannot grade student %s (%s) in course %s because of exception: %s',
                    student.username,
                    student.id,
                    course_id,
                    exc.message
                )
                yield student, {}, exc.message
