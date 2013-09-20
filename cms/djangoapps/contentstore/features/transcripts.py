# disable missing docstring
# pylint: disable=C0111

from lettuce import world, step

delay = 1

error_messages = {
    'url_format': u'Incorrect url format.',
    'file_type': u'Link types should be unique.',
}

selectors = {
    'error_bar': '.transcripts-error-message',
    'url_inputs': '.videolist-settings-item input.input',
    'collapse_link': '.collapse-action.collapse-setting',
    'collapse_bar': '.videolist-extra-videos',
}


@step('I clear fields$')
def clear_fields(_step):
    world.css_click('.metadata-videolist-enum .setting-clear')


@step('I clear field number (.+)$')
def clear_field(_step, index):
    index = int(index) - 1
    world.css_fill(selectors['url_inputs'], '', index)


@step('I (.*)see (.*)error message$')
def i_see_error_message(_step, not_error, error):
    world.wait(delay)
    if not_error:
        assert not world.css_visible(selectors['error_bar'])
    else:
        assert world.css_has_text(selectors['error_bar'], error_messages[error.strip()])


@step('I enter a (.+) source to field number (\d+)$')
def i_enter_a_source(_step, link, index):
    index = int(index) - 1

    if index is not 0 and not world.css_visible(selectors['collapse_bar']):
        world.css_click(selectors['collapse_link'])
        assert world.css_visible(selectors['collapse_bar'])

    world.css_fill(selectors['url_inputs'], link, index)
