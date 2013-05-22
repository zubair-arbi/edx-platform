from django.contrib.auth.models import User
from django.test import RequestFactory


class ExternalGrader(object):
    def __init__(self, module_id, course_id, user_id):
        self._module_context = {
            'module_id': module_id,
            'course_id': course_id,
            'user_id': user_id
        }

    def submit(self, queue_name, payload):
        from external_graders import tasks

        context = self._module_context

        # TODO: get proper queue name
        if queue_name is None:
            queue_name = 'the_queue'

        # Create subtasks
        s1 = tasks.queue_grader.s(context, payload).set(queue=queue_name)
        s2 = tasks.update_grader.s()

        # Call subtasks
        # TODO: add error handler
        r = (s1 | s2).apply_async()

        return ExternalGraderPromise(r)


class ExternalGraderPromise(object):
    def __init__(self, async_result):
        self._async_result = async_result

    @property
    def ready(self):
        return self._async_result.ready()

    @property
    def correct_map(self):
        if self._async_result.ready():
            return self.async_result.get()
        else:
            return None

    @property
    def error(self):
        return None
