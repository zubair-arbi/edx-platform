# disable missing docstring
# pylint: disable=C0111

from lettuce import world, step

@step('I enter an incorrect URL$')
def i_edit_url(_step):
    world.css_fill('#metadata-videolist-entry_19', 'ht:/f.c')

@step('I see error message$')
def i_see_error_message(_step):
    assert world.css_text('.transcripts-error-message') == u'Incorrect url format.'

@step('I enter a (.+) source to field number (.+)$')
def i_enter_two_source_same_format(_step, link, index):
    import ipdb; ipdb.set_trace()

    if int(index) == 0:
        world.css_click('.collapse-action.collapse-setting')

    world.css_fill('.videolist-settings-item .input', link, int(index))

@step('I see same format error message$')
def i_see_same_format_error_message(_step):
    import ipdb; ipdb.set_trace()

    assert world.css_text('.transcripts-error-message') == u''
