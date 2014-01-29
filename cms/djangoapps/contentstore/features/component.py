#pylint: disable=C0111
#pylint: disable=W0621

# Lettuce formats proposed definitions for unimplemented steps with the
# argument name "step" instead of "_step" and pylint does not like that.
#pylint: disable=W0613

from lettuce import world, step
from nose.tools import assert_true, assert_in  # pylint: disable=E0611


@step(u'I add this type of single step component:$')
def add_a_single_step_component(step):
    for step_hash in step.hashes:
        component = step_hash['Component']
        assert_in(component, ['Discussion', 'Video'])

        world.create_component_instance(
            step=step,
            category='{}'.format(component.lower()),
        )


@step(u'I see this type of single step component:$')
def see_a_single_step_component(step):
    for step_hash in step.hashes:
        component = step_hash['Component']
        assert_in(component, ['Discussion', 'Video'])
        component_css = 'section.xmodule_{}Module'.format(component)
        assert_true(world.is_css_present(component_css),
                    "{} couldn't be found".format(component))


@step(u'I add this type of( Advanced)? (HTML|Problem) component:$')
def add_a_multi_step_component(step, is_advanced, category):
    for step_hash in step.hashes:
        world.create_component_instance(
            step=step,
            category='{}'.format(category.lower()),
            component_type=step_hash['Component'],
            is_advanced=bool(is_advanced),
        )


@step(u'I see (HTML|Problem) components in this order:')
def see_a_multi_step_component(step, category):

    # Wait for all components to finish rendering
    selector = 'li.component section.xblock-student_view'
    world.wait_for(lambda _: len(world.css_find(selector)) == len(step.hashes))

    for idx, step_hash in enumerate(step.hashes):

        if category == 'HTML':
            html_matcher = {
                'Text':
                    '\n    \n',
                'Announcement':
                    '<p> Words of encouragement! This is a short note that most students will read. </p>',
                'Zooming Image':
                    '<h2>ZOOMING DIAGRAMS</h2>',
                'E-text Written in LaTeX':
                    '<h2>Example: E-text page</h2>',
            }
            actual_html = world.css_html(selector, index=idx)
            assert_in(html_matcher[step_hash['Component']], actual_html)
        else:
            actual_text = world.css_text(selector, index=idx)
            assert_in(step_hash['Component'].upper(), actual_text)


@step(u'I see a "([^"]*)" Problem component$')
def see_a_problem_component(step, category):
    component_css = 'section.xmodule_CapaModule'
    assert_true(world.is_css_present(component_css),
                'No problem was added to the unit.')

    problem_css = 'li.component section.xblock-student_view'
    actual_text = world.css_text(problem_css)
    assert_in(category.upper(), actual_text)


@step(u'I add a "([^"]*)" "([^"]*)" component$')
def add_component_category(step, component, category):
    assert category in ('single step', 'HTML', 'Problem', 'Advanced Problem')
    given_string = 'I add this type of {} component:'.format(category)
    step.given('{}\n{}\n{}'.format(given_string, '|Component|', '|{}|'.format(component)))


@step(u'I delete all components$')
def delete_all_components(step):
    count = len(world.css_find('ol.components li.component'))
    step.given('I delete "' + str(count) + '" component')


@step(u'I delete "([^"]*)" component$')
def delete_components(step, number):
    world.wait_for_xmodule()
    delete_btn_css = 'a.delete-button'
    prompt_css = 'div#prompt-warning'
    btn_css = '{} a.button.action-primary'.format(prompt_css)
    saving_mini_css = 'div#page-notification .wrapper-notification-mini'
    for _ in range(int(number)):
        world.css_click(delete_btn_css)
        assert_true(
            world.is_css_present('{}.is-shown'.format(prompt_css)),
            msg='Waiting for the confirmation prompt to be shown')

        # Pressing the button via css was not working reliably for the last component
        # when run in Chrome.
        if world.browser.driver_name is 'Chrome':
            world.browser.execute_script("$('{}').click()".format(btn_css))
        else:
            world.css_click(btn_css)

        # Wait for the saving notification to pop up then disappear
        if world.is_css_present('{}.is-shown'.format(saving_mini_css)):
            world.css_find('{}.is-hiding'.format(saving_mini_css))


@step(u'I see no components')
def see_no_components(steps):
    assert world.is_css_not_present('li.component')


@step(u'I delete a component')
def delete_one_component(step):
    world.css_click('a.delete-button')


@step(u'I edit and save a component')
def edit_and_save_component(step):
    world.css_click('.edit-button')
    world.css_click('.save-button')


@step(u'I duplicate the "([^"]*)" component$')
def duplicated_component(step, index):
    duplicate_btn_css = 'a.duplicate-button'
    world.css_click(duplicate_btn_css, int(index))


@step(u'I see a Problem component with display name "([^"]*)" in position "([^"]*)"$')
def see_component_in_position(step, display_name, index):
    component_css = 'section.xmodule_CapaModule'

    def find_problem(_driver):
        return world.css_text(component_css, int(index)).startswith(display_name.upper())

    world.wait_for(find_problem, timeout_msg='Did not find the duplicated problem')
