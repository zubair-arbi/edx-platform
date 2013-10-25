
def user_is_article_course_staff(user, article):
    """
    The root of a course wiki is /<course_number>. This means multiple courses
    share the same wiki root e.g. MITX/Phy101/Spring and HarvardX/Phy101/Fall
    share the same wiki root /Phy101.

    This looks at the second level ancestor of the article and returns True if
    the user belongs to a group whose name starts with 'instructor_' or
    'staff_' and contains '/<second_level_ancestor_slug>/'. So if the user is
    staff on course MITX/Phy101/Spring they will be in
    'instructor_MITX/Phy101/Spring' or 'staff_MITX/Phy101/Spring' groups and
    so this will return True.
    """

    # We assume that the second level ancestor is a course wiki root
    course_number = article_second_level_ancestor_slug(article)

    if course_number is None:
        return False

    if user_is_staff_on_course_number(user, course_number):
        return True

    # The wiki expects article slugs to contain at least one non-digit so if
    # the course number is just a number the course wiki root slug is set to
    # be '<course_number>_'.
    if course_number.endswith('_') and user_is_staff_on_course_number(user, course_number[:-1]):
        return True

    return False

def user_is_staff_on_course_number(user, course_number):

    # Find any user groups with the course number
    # Note that in django+MySQL icontains is case-sensitive if collation is case-sensitive
    # and case-insensitive if collation is case-insensitive (https://code.djangoproject.com/ticket/9682)
    user_course_groups = user.groups.filter(name__icontains='/{0}/'.format(course_number))

    # Filter down to instructor and staff groups
    user_course_staff_groups = filter(lambda g: g.name.startswith(('instructor_', 'staff_')) , user_course_groups)

    return user_course_staff_groups # So if user is in a staff group of the course

def article_second_level_ancestor_slug(article):
    """
    This returns the slug of the course wiki root. Examples:
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
    except:
        return None

    # Ancestors of /Phy101/Mechanics/Acceleration/ is a list of URLPaths
    # ['Root', 'Phy101', 'Mechanics']
    ancestors = urlpath.cached_ancestors

    level_two_ancestor_urlpath = None

    if len(ancestors) == 0: # It is the wiki root article.
       level_two_ancestor_urlpath = None
    elif len(ancestors) == 1: # It is a course wiki root article.
        level_two_ancestor_urlpath = urlpath
    else: # It is an article inside a course wiki.
        level_two_ancestor_urlpath = ancestors[1]

    if level_two_ancestor_urlpath is not None:
        return level_two_ancestor_urlpath.slug

    return None
