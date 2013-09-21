# disable missing docstring
# pylint: disable=C0111

from lettuce import world, step

delay = 1

error_messages = {
    'url_format': u'Incorrect url format.',
    'file_type': u'Link types should be unique.',
}

STATUSES = {
    'found': u'Timed Transcripts Found',
    'not found': u'No Timed Transcripts',
    'replace': u'Timed Transcripts Conflict'
}

selectors = {
    'error_bar': '.transcripts-error-message',
    'url_inputs': '.videolist-settings-item input.input',
    'collapse_link': '.collapse-action.collapse-setting',
    'collapse_bar': '.videolist-extra-videos',
    'status_bar': '.transcripts-message-status'
}

# button type , button css selector, button message
BUTTONS = {
    'import': ('.setting-import',  'Import from YouTube'),
    'download_to_edit': ('.setting-download', 'Download to Edit'),
    'upload_new_timed_transcripts': ('.setting-upload',  'Upload New Timed Transcripts'),
    'replace': ('.setting-replace', 'Yes, Replace EdX Timed Transcripts with YouTube Timed Transcripts')
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
def i_see_button(_step, not_see, button_type):
    world.wait(delay)
    button = button_type.strip()
    if BUTTONS.get(button):
        if not_see:
            assert world.is_css_not_present(BUTTONS[button][0])
        else:
            assert world.css_has_text(BUTTONS[button][0], BUTTONS[button][1])
    else:
        assert False  # not implemented


@step('I click (.*)button$')
def click_button(_step, button_type):
    world.wait(delay)
    button = button_type.strip()
    if BUTTONS.get(button):
        world.css_click(BUTTONS[button][0])
    else:
        assert False  # not implemented


@step('I remove (.*)transcripts id from store')
def remove_transcripts_from_store(_step, subs_id):
    """Remove from store, if transcripts content exists."""
    from xmodule.contentstore.content import StaticContent
    from xmodule.contentstore.django import contentstore
    from xmodule.exceptions import NotFoundError
    filename = 'subs_{0}.srt.sjson'.format(subs_id.strip())
    content_location = StaticContent.compute_location(
        world.scenario_dict['COURSE'].org,
        world.scenario_dict['COURSE'].number,
        filename
    )
    try:
        content = contentstore().find(content_location)
        contentstore().delete(content.get_id())
        print('Transcript file was removed from store.')
    except NotFoundError:
        print('Transcript file was NOT found and not removed.')



@step('I enter a (.+) source to field number (\d+)$')
def i_enter_a_source(_step, link, index):
    index = int(index) - 1
    world.wait(delay)

    if index is not 0 and not world.css_visible(selectors['collapse_bar']):
        world.css_click(selectors['collapse_link'])
        assert world.css_visible(selectors['collapse_bar'])

    world.css_fill(selectors['url_inputs'], link, index)
