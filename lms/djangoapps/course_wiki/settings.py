from course_wiki.utils import user_is_article_course_staff

def CAN_DELETE(article, user):
    return user.is_staff or user.is_superuser or user_is_article_course_staff(user, article)

def CAN_MODERATE(article, user):
    return user.is_staff or user.is_superuser or user_is_article_course_staff(user, article)

def CAN_CHANGE_PERMISSIONS(article, user):
    return user.is_staff or user.is_superuser or user_is_article_course_staff(user, article)

def CAN_ASSIGN(article, user):
    return user.is_staff or user.is_superuser or user_is_article_course_staff(user, article)

def CAN_ASSIGN_OWNER(article, user):
    return user.is_staff or user.is_superuser or user_is_article_course_staff(user, article)
