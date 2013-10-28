from django.core.exceptions import ObjectDoesNotExist

def user_is_article_course_staff(user, article):
    """
    The root of a course wiki is /<course_number>. This means in case there
    are two courses which have the same course_number they will end up with
    the same course wiki root e.g. MITX/Phy101/Spring and HarvardX/Phy101/Fall
    will share /Phy101.

    This looks at the course wiki root of the article and returns True if
    the user belongs to a group whose name starts with 'instructor_' or
    'staff_' and contains '/<course_wiki_root_slug>/'. So if the user is
    staff on course MITX/Phy101/Spring they will be in
    'instructor_MITX/Phy101/Spring' or 'staff_MITX/Phy101/Spring' groups and
    so this will return True.
    """

    course_slug = article_course_wiki_root_slug(article)

    if course_slug is None:
        return False

    if user_is_staff_on_course_number(user, course_slug):
        return True

    # The wiki expects article slugs to contain at least one non-digit so if
    # the course number is just a number the course wiki root slug is set to
    # be '<course_number>_'. Again this means that courses with course numbers
    # like '202' and '202_' will share the same course wiki root.
    if (course_slug.endswith('_') and course_wiki_slug_is_numerical(course_slug[:-1]) and
            user_is_staff_on_course_number(user, course_slug[:-1])):
        return True

    return False

def course_wiki_slug_is_numerical(course_wiki_slug):
    try:
        # if the float() doesn't throw an exception it's a number
        float(course_wiki_slug)
    except:
        pass
    else:
        return True
    return False

def course_wiki_slug(course):
    course_wiki_slug = course.wiki_slug

    # cdodge: fix for cases where self.location.course can be interpreted as an number rather than
    # a string. We're seeing in Studio created courses that people often will enter in a stright number
    # for 'course' (e.g. 201). This Wiki library expects a string to "do the right thing". We haven't noticed this before
    # because - to now - 'course' has always had non-numeric characters in them
    if course_wiki_slug_is_numerical(course_wiki_slug):
        course_wiki_slug = course_wiki_slug + "_"

    return course_wiki_slug

def user_is_staff_on_course_number(user, course_number):

    # Find any user groups whose name contains the course number
    # Note that in django+MySQL icontains is case-sensitive if collation is case-sensitive
    # and case-insensitive if collation is case-insensitive (https://code.djangoproject.com/ticket/9682)
    user_course_groups = user.groups.filter(name__icontains='/{0}/'.format(course_number))

    # Filter down to instructor and staff groups
    user_course_staff_groups = filter(lambda g: g.name.startswith(('instructor_', 'staff_')) , user_course_groups)

    if user_course_staff_groups:
        return True

    return False

def article_course_wiki_root_slug(article):
    """
    We assume the second level ancestor is the course wiki root. Examples:
    / returns None
    /Phy101 returns 'Phy101'
    /Phy101/Mechanics returns 'Phy101'
    /Chem101/Metals/Iron returns 'Chem101'

    Note that someone can create an article /random-article/sub-article on the
    wiki. In this case this function will return 'some-random-article' even
    if no course with course number 'some-random-article' exists.
    """

    try:
        urlpath = article.urlpath_set.get()
    except ObjectDoesNotExist:
        return None

    # Ancestors of /Phy101/Mechanics/Acceleration/ is a list of URLPaths
    # ['Root', 'Phy101', 'Mechanics']
    ancestors = urlpath.cached_ancestors

    course_wiki_root_urlpath = None

    if len(ancestors) == 0: # It is the wiki root article.
       course_wiki_root_urlpath = None
    elif len(ancestors) == 1: # It is a course wiki root article.
        course_wiki_root_urlpath = urlpath
    else: # It is an article inside a course wiki.
        course_wiki_root_urlpath = ancestors[1]

    if course_wiki_root_urlpath is not None:
        return course_wiki_root_urlpath.slug

    return None
