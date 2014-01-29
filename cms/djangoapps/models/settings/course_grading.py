from datetime import timedelta
from contentstore.utils import get_modulestore
from xmodule.modulestore.django import loc_mapper
from xblock.fields import Scope


class CourseGradingModel(object):
    """
    Basically a DAO and Model combo for CRUD operations pertaining to grading policy.
    """
    # Within this class, allow access to protected members of client classes.
    # This comes up when accessing kvs data and caches during kvs saves and modulestore writes.
    def __init__(self, course_descriptor):
        self.graders = [
            CourseGradingModel.jsonize_grader(i, grader) for i, grader in enumerate(course_descriptor.raw_grader)
        ]  # weights transformed to ints [0..100]
        self.grade_cutoffs = course_descriptor.grade_cutoffs
        self.grace_period = CourseGradingModel.convert_set_grace_period(course_descriptor)

    @classmethod
    def fetch(cls, course_locator):
        """
        Fetch the course grading policy for the given course from persistence and return a CourseGradingModel.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_locator)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        model = cls(descriptor)
        return model

    @staticmethod
    def fetch_grader(course_location, index):
        """
        Fetch the course's nth grader
        Returns an empty dict if there's no such grader.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        index = int(index)
        if len(descriptor.raw_grader) > index:
            return CourseGradingModel.jsonize_grader(index, descriptor.raw_grader[index])

        # return empty model
        else:
            return {"id": index,
                    "type": "",
                    "min_count": 0,
                    "drop_count": 0,
                    "short_label": None,
                    "weight": 0
                    }

    @staticmethod
    def update_from_json(course_locator, jsondict):
        """
        Decode the json into CourseGradingModel and save any changes. Returns the modified model.
        Probably not the usual path for updates as it's too coarse grained.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_locator)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        graders_parsed = [CourseGradingModel.parse_grader(jsonele) for jsonele in jsondict['graders']]

        descriptor.raw_grader = graders_parsed
        descriptor.grade_cutoffs = jsondict['grade_cutoffs']

        get_modulestore(course_old_location).update_item(
            course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.content)
        )

        CourseGradingModel.update_grace_period_from_json(course_locator, jsondict['grace_period'])

        return CourseGradingModel.fetch(course_locator)

    @staticmethod
    def update_grader_from_json(course_location, grader):
        """
        Create or update the grader of the given type (string key) for the given course. Returns the modified
        grader which is a full model on the client but not on the server (just a dict)
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        # parse removes the id; so, grab it before parse
        index = int(grader.get('id', len(descriptor.raw_grader)))
        grader = CourseGradingModel.parse_grader(grader)

        if index < len(descriptor.raw_grader):
            descriptor.raw_grader[index] = grader
        else:
            descriptor.raw_grader.append(grader)

        get_modulestore(course_old_location).update_item(
            course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.content)
        )

        return CourseGradingModel.jsonize_grader(index, descriptor.raw_grader[index])

    @staticmethod
    def update_cutoffs_from_json(course_location, cutoffs):
        """
        Create or update the grade cutoffs for the given course. Returns sent in cutoffs (ie., no extra
        db fetch).
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)
        descriptor.grade_cutoffs = cutoffs

        get_modulestore(course_old_location).update_item(
            course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.content)
        )

        return cutoffs

    @staticmethod
    def update_grace_period_from_json(course_location, graceperiodjson):
        """
        Update the course's default grace period. Incoming dict is {hours: h, minutes: m} possibly as a
        grace_period entry in an enclosing dict. It is also safe to call this method with a value of
        None for graceperiodjson.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        # Before a graceperiod has ever been created, it will be None (once it has been
        # created, it cannot be set back to None).
        if graceperiodjson is not None:
            if 'grace_period' in graceperiodjson:
                graceperiodjson = graceperiodjson['grace_period']

            grace_timedelta = timedelta(**graceperiodjson)
            descriptor.graceperiod = grace_timedelta

            get_modulestore(course_old_location).update_metadata(
                course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.settings)
            )

    @staticmethod
    def delete_grader(course_location, index):
        """
        Delete the grader of the given type from the given course.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        index = int(index)
        if index < len(descriptor.raw_grader):
            del descriptor.raw_grader[index]
            # force propagation to definition
            descriptor.raw_grader = descriptor.raw_grader

        get_modulestore(course_old_location).update_item(
            course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.content)
        )

    @staticmethod
    def delete_grace_period(course_location):
        """
        Delete the course's grace period.
        """
        course_old_location = loc_mapper().translate_locator_to_location(course_location)
        descriptor = get_modulestore(course_old_location).get_item(course_old_location)

        del descriptor.graceperiod

        get_modulestore(course_old_location).update_metadata(
            course_old_location, descriptor.get_explicitly_set_fields_by_scope(Scope.settings)
        )

    @staticmethod
    def get_section_grader_type(location):
        old_location = loc_mapper().translate_locator_to_location(location)
        descriptor = get_modulestore(old_location).get_item(old_location)
        return {
            "graderType": descriptor.format if descriptor.format is not None else 'notgraded',
            "location": unicode(location),
        }

    @staticmethod
    def update_section_grader_type(descriptor, grader_type):
        if grader_type is not None and grader_type != u'notgraded':
            descriptor.format = grader_type
            descriptor.graded = True
        else:
            del descriptor.format
            del descriptor.graded

        get_modulestore(descriptor.location).update_metadata(
            descriptor.location, descriptor.get_explicitly_set_fields_by_scope(Scope.settings)
        )
        return {'graderType': grader_type}

    @staticmethod
    def convert_set_grace_period(descriptor):
        # 5 hours 59 minutes 59 seconds => converted to iso format
        rawgrace = descriptor.graceperiod
        if rawgrace:
            hours_from_days = rawgrace.days * 24
            seconds = rawgrace.seconds
            hours_from_seconds = int(seconds / 3600)
            hours = hours_from_days + hours_from_seconds
            seconds -= hours_from_seconds * 3600
            minutes = int(seconds / 60)
            seconds -= minutes * 60

            graceperiod = {'hours': 0, 'minutes': 0, 'seconds': 0}
            if hours > 0:
                graceperiod['hours'] = hours

            if minutes > 0:
                graceperiod['minutes'] = minutes

            if seconds > 0:
                graceperiod['seconds'] = seconds

            return graceperiod
        else:
            return None

    @staticmethod
    def parse_grader(json_grader):
        # manual to clear out kruft
        result = {"type": json_grader["type"],
                  "min_count": int(json_grader.get('min_count', 0)),
                  "drop_count": int(json_grader.get('drop_count', 0)),
                  "short_label": json_grader.get('short_label', None),
                  "weight": float(json_grader.get('weight', 0)) / 100.0
                  }

        return result

    @staticmethod
    def jsonize_grader(i, grader):
        grader['id'] = i
        if grader['weight']:
            grader['weight'] *= 100
        if not 'short_label' in grader:
            grader['short_label'] = ""

        return grader
