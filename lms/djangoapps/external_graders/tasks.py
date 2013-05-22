from djcelery import celery

from external_graders.helper import update_score

# external task (maybe use decorator?)
@celery.task
def queue_grader(_context, _payload):
    # external grader
    return {'context': _context, 'response': 'foo'}

@celery.task
def update_grader(result):
    # context = result['context']
    # response = result['response']

    # cmap = update_score(
    #     module_id=context['module_id'],
    #     course_id=context['course_id'],
    #     user_id=context['user_id'],
    #     response=response
    # )

    cmap = {}
    return cmap
