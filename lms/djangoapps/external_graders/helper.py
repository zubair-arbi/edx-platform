from xmodule.modulestore.django import modulestore


def update_score(module_id, course_id, user_id, response):
    from courseware import module_render
    from courseware.model_data import ModelDataCache

    user = User.objects.get(id=user_id)

    descriptor = modulestore().get_instance(course_id, module_id)

    cache = ModelDataCache.cache_for_descriptor_descendents(
        course_id,
        user,
        descriptor,
        depth=0,
        select_for_update=True
    )

    # To instanciate the module, we need a web request it is
    # requiredby the tracking application. Create a fake one since we
    # don't have one in the current context.
    request = RequestFactory().get('/xmodule_callback')

    module = module_render.get_module(
        user,
        request,
        module_id,
        cache,
        course_id,
        grade_bucket_type='external'
    )

    # TODO: check if it has update_score (could be ErrorModule)
    cmap = module.update_score({'xqueue_body': response, 'queuekey': ''})

    return cmap
