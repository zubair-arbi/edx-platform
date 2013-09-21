# disable missing docstring
# pylint: disable=C0111

from lettuce import world, step

delay = 1

error_messages = {
    'url_format': u'Incorrect url format.',
    'file_type': u'Link types should be unique.',
}

STATUSES = {
    'found': u'Timed Transcripts Found.',
    'not found': u'No Timed Transcripts'
}

selectors = {
    'error_bar': '.transcripts-error-message',
    'url_inputs': '.videolist-settings-item input.input',
    'collapse_link': '.collapse-action.collapse-setting',
    'collapse_bar': '.videolist-extra-videos',
    'status_bar': '.transcripts-message-status'
}


@step('I clear fields$')
def clear_fields(_step):
    world.css_click('.metadata-videolist-enum .setting-clear')


@step('I clear field number (.+)$')
def clear_field(_step, index):
    index = int(index) - 1
    world.css_fill(selectors['url_inputs'], '', index)


@step('I expect (.+) inputs are disabled$')
def inputs_are_disabled(_step, indexes):
    index_list = [int(i.strip()) - 1 for i in indexes.split(',')]
    for index in index_list:
        el = world.css_find(selectors['url_inputs'])[index]
        assert el['disabled']


@step('I expect inputs are enabled$')
def inputs_are_enabled(_step):
    for index in range(3):
        el = world.css_find(selectors['url_inputs'])[index]
        assert not el['disabled']


@step('I (.*)see (.*)error message$')
def i_see_error_message(_step, not_error, error):
    world.wait(delay)
    if not_error:
        assert not world.css_visible(selectors['error_bar'])
    else:
        assert world.css_has_text(selectors['error_bar'], error_messages[error.strip()])


@step('I (.*)see (.*)status message$')
def i_see_status_message(_step, not_see, status):
    world.wait(delay)
    if not_see:
        assert not world.css_visible(selectors['status_bar'])
    else:
        assert world.css_has_text(selectors['status_bar'], STATUSES[status.strip()])


@step('I (.*)see (.*)button$')
def i_see_import_from_youtube_button(_step, not_see, button_type):
    world.wait(delay)
    if button_type.strip() == 'import':
        if not_see:
            assert world.is_css_not_present('.setting-import')
        else:
            assert world.css_has_text('.setting-import', 'Import from YouTube')
    elif button_type.strip() == 'download_to_edit':
        if not_see:
            assert world.is_css_not_present('.setting-download')
        else:
            assert world.css_has_text('.setting-download', 'Download to Edit')

    else:
        assert False  # not imlemented


@step('I click (.*)button$')
def click_button(_step, button_type):
    world.wait(delay)
    if button_type.strip() == 'import':
        world.css_click('.setting-import')
        import ipdb; ipdb.set_trace()
    # elif button_type.strip() == 'download_to_edit':
    #     if not_see:
    #         assert world.is_css_not_present('.setting-download')
    #     else:
    #         assert world.css_has_text('.setting-download', 'Download to Edit')
    else:
        assert False  # not imlemented


@step('I enter a (.+) source to field number (\d+)$')
def i_enter_a_source(_step, link, index):
    index = int(index) - 1
    world.wait(delay)

    if index is not 0 and not world.css_visible(selectors['collapse_bar']):
        world.css_click(selectors['collapse_link'])
        assert world.css_visible(selectors['collapse_bar'])

    world.css_fill(selectors['url_inputs'], link, index)
