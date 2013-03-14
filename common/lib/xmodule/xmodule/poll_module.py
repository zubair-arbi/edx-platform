"""Poll module is ungraded xmodule used by students to
to do set of polls.

On the client side we show:
If student does not yet anwered - Question with set of choices.
If student have answered - Question with statistics for each answers.

Student can't change his answer.
"""

import cgi
import json
import logging
from copy import deepcopy
from collections import OrderedDict

from lxml import etree
from pkg_resources import resource_string

from xmodule.x_module import XModule
from xmodule.stringify import stringify_children
from xmodule.mako_module import MakoModuleDescriptor
from xmodule.xml_module import XmlDescriptor

log = logging.getLogger(__name__)


class XField(dict):
    def __init__(self, field_name, definition_id):
        # Get data from DB by definition_id using
        # courseware_xmodulecontentfield table.
        from courseware.models import XModuleContentField

        self.field_name = field_name
        self.definition_id = definition_id

        try:
            self.db_data = XModuleContentField.objects.get(
                definition_id=definition_id)
            value = json.loads(self.db_data.value)
        except XModuleContentField.DoesNotExist:
            self.db_data = None
            value = {}

        super(XField, self).__init__(value)

    def save(self):
        """Save data to DB using
        courseware_xmodulecontentfield table.
        """
        from courseware.models import XModuleContentField

        json_value = json.dumps(self)

        if self.db_data:
            self.db_data.value = json_value

            # TODO: in django 1.5 use .save(update_fields=['value'])
            self.db_data.save()
        else:
            self.db_data = XModuleContentField.objects.create(
                field_name=self.field_name,
                definition_id=self.definition_id,
                value=json_value)



class PollModule(XModule):
    """Poll Module"""
    js = {
      'coffee': [resource_string(__name__, 'js/src/javascript_loader.coffee')],
      'js': [resource_string(__name__, 'js/src/poll/logme.js'),
             resource_string(__name__, 'js/src/poll/poll.js'),
             resource_string(__name__, 'js/src/poll/poll_main.js')]
         }
    css = {'scss': [resource_string(__name__, 'css/poll/display.scss')]}
    js_module_name = "Poll"

    # Name of poll to use in links to this poll


    def __init__(self, system, location, definition, descriptor, instance_state=None,
                 shared_state=None, **kwargs):
        XModule.__init__(self, system, location, definition, descriptor, instance_state,
                         shared_state, **kwargs)
        self.voted = None
        self.poll_answer = ''

        self.poll_answers = XField('poll_answers', self.location.url())

        if instance_state is not None:
            instance_state = json.loads(instance_state)
            self.voted = instance_state['voted']
            self.poll_answer = instance_state['poll_answer']


    def get_instance_state(self):
        state = {}
        state['voted'] = self.voted
        state['poll_answer'] = self.poll_answer
        return json.dumps(state)

    def handle_ajax(self, dispatch, get):
        """Ajax handler.

        Args:
            dispatch: string request slug
            get: dict request get parameters

        Returns:
            json string
        """
        self.dump_poll()
        if dispatch in self.poll_answers and not self.voted:
            self.poll_answers[dispatch] += 1
            self.poll_answers.save()

            self.voted = True
            self.poll_answer = dispatch
            return json.dumps({'poll_answers': self.poll_answers,
                               'total': sum(self.poll_answers.values()),
                               'callback': {'objectName': 'Conditional'}
                               })
        elif dispatch == 'get_state':
            return json.dumps({'poll_answer': self.poll_answer,
                               'poll_answers': self.poll_answers,
                               'total': sum(self.poll_answers.values())
                               })
        elif dispatch == 'reset_poll' and self.voted and \
                self.descriptor.metadata.get('reset', 'True').lower() != 'false':
            self.voted = False

            self.poll_answers[self.poll_answer] -= 1
            self.poll_answers.save()

            self.poll_answer = ''
            return json.dumps({'status': 'success'})
        else:  # return error message
            return json.dumps({'error': 'Unknown Command!'})

    def get_html(self):
        """Renders parameters to template."""
        params = {
                  'element_id': self.location.html_id(),
                  'element_class': self.location.category,
                  'ajax_url': self.system.ajax_url,
                  'configuration_json': self.dump_poll(),
                  }
        self.content = self.system.render_template('poll.html', params)
        return self.content

    def dump_poll(self):
        """Dump poll information.

        Returns:
            string - Serialize json.
        """

        answers_to_json = OrderedDict()

         # Fill self.poll_answers, prepare data for template context.
        for answer in self.definition.get('answers'):
            # Set default count for answer = 0.
            if answer['id'] not in self.poll_answers:
                self.poll_answers[answer['id']] = 0
            answers_to_json[answer['id']] = cgi.escape(answer['text'])
        self.poll_answers.save()

        return json.dumps({'answers': answers_to_json,
            'question': cgi.escape(self.definition.get('question')),
            # to show answered poll after reload:
            'poll_answer': self.poll_answer,
            'poll_answers': self.poll_answers if self.voted else {},
            'total': sum(self.poll_answers.values()) if self.voted else 0,
            'reset': str(self.descriptor.metadata.get('reset', 'true')).lower()})


class PollDescriptor(MakoModuleDescriptor, XmlDescriptor):
    _tag_name = 'poll_question'
    _child_tag_name = 'answer'

    module_class = PollModule
    template_dir_name = 'poll'
    stores_state = True

    # display_name = String(help="Display name for this module", scope=Scope.settings)
    # id = String(help="ID attribute for this module", scope=Scope.settings)

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        """Pull out the data into dictionary.

        Args:
            xml_object: xml from file.
            system: `system` object.

        Returns:
            (definition, children) - tuple
            definition - dict:
                {
                    'answers': <List of answers>,
                    'question': <Question string>
                }
        """
        # Check for presense of required tags in xml.
        if len(xml_object.xpath(cls._child_tag_name)) == 0:
            raise ValueError("Poll_question definition must include \
                at least one 'answer' tag")

        xml_object_copy = deepcopy(xml_object)
        answers = []
        for element_answer in xml_object_copy.findall(cls._child_tag_name):
            answer_id = element_answer.get('id', None)
            if answer_id:
                answers.append({
                    'id': answer_id,
                    'text': stringify_children(element_answer)
                })
            xml_object_copy.remove(element_answer)

        definition = {
            'answers': answers,
            'question': stringify_children(xml_object_copy)
        }
        children = []
        definition['children'] = children
        return definition

    def definition_to_xml(self, resource_fs):
        """Return an xml element representing to this definition."""
        poll_str = '<{tag_name}>{text}</{tag_name}>'.format(
            tag_name=self._tag_name, text=self.question)
        xml_object = etree.fromstring(poll_str)
        xml_object.set('display_name', self.display_name)
        xml_object.set('id', self.id)

        def add_child(xml_obj, answer):
            child_str = '<{tag_name} id="{id}">{text}</{tag_name}>'.format(
                tag_name=self._child_tag_name, id=answer['id'],
                text=answer['text'])
            child_node = etree.fromstring(child_str)
            xml_object.append(child_node)

        for answer in self.answers:
            add_child(xml_object, answer)

        return xml_object
