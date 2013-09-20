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
    'collapse_bar': '.collapse-action.collapse-setting'
}

@step('I see (.+) error message$')
def i_see_error_message(_step, error):
    world.wait(delay)

    assert world.css_has_text(selectors['error_bar'], error_messages[error])


@step('I enter a (.+) source to field number (.+)$')
def i_enter_a_source(_step, link, index):
    index = int(index) - 1
    if index is not 0:
        world.css_click(selectors['collapse_bar'])

    world.css_fill(selectors['url_inputs'], link, index)

