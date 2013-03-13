import json
import logging

from xmodule.x_module import XModule
from xmodule.modulestore import Location
from xmodule.seq_module import SequenceDescriptor

from pkg_resources import resource_string

log = logging.getLogger('mitx.' + __name__)


from xmodule.modulestore.exceptions import ItemNotFoundError
from lxml import etree


class ConditionalModule(XModule):
    """
    Blocks child module from showing unless certain conditions are met.

    Example old style:

        <conditional condition="require_completed" required="tag/url_name1&tag/url_name2">
            <video url_name="secret_video" />
        </conditional>

        <conditional condition="require_attempted" required="tag/url_name1&tag/url_name2">
            <video url_name="secret_video" />
        </conditional>

    Example new style:

        <conditional sources="i4x://.../problem_1; i4x://.../problem_2" completed="True">
            <show sources="i4x://.../test_6; i4x://.../Avi_resources"/>
            <video url_name="secret_video" />
        </conditional>

        <conditional> tag attributes:
            sources - location id of required modules, separated by ';'

            completed - map to `is_completed` module method
            attempted - map to `is_attempted` module method
            poll_answer - map to `poll_answer` module attribute
            voted - map to `voted` module attribute

        <conditional> tag attributes:
            sources - location id of modules, separated by ';'
    """
    js = {'coffee': [resource_string(__name__, 'js/src/conditional/display.coffee'),
                     resource_string(__name__, 'js/src/collapsible.coffee'),
                     resource_string(__name__, 'js/src/javascript_loader.coffee'),
                    ]}

    js_module_name = "Conditional"
    css = {'scss': [resource_string(__name__, 'css/capa/display.scss')]}


    # def __init__(self, system, location, definition, descriptor, instance_state=None, shared_state=None, **kwargs):
    #     """
    #     In addition to the normal XModule init, provide:

    #         self.condition            = string describing condition required

    #     """
    #     XModule.__init__(self, system, location, definition, descriptor, instance_state, shared_state, **kwargs)
    #     self.contents = None
    #     self.condition = self.metadata.get('condition', '')
    #     self._get_required_modules()
    #     children = self.get_display_items()
    #     if children:
    #         self.icon_class = children[0].get_icon_class()
        #log.debug('conditional module required=%s' % self.required_modules_list)

    # def _get_required_modules(self):
    #     self.required_modules = []
    #     for descriptor in self.descriptor.get_required_module_descriptors():
    #         module = self.system.get_module(descriptor)
    #         self.required_modules.append(module)
    #     #log.debug('required_modules=%s' % (self.required_modules))

    # Map
    # key: <tag attribute in xml>
    # value: <name of module attribute>
    conditions_map = {
        'poll_answer': 'poll_answer',  # poll_question attr
        'completed': 'is_completed',  # capa_problem attr
        'attempted': 'is_attempted',  # capa_problem attr
        'voted': 'voted'  # poll_question attr
    }


    def _get_condition(self):
        if self.descriptor.xml_attributes.get('required'):
            #old style:
            xml_value = (self.descriptor.xml_attributes.get('required').
                    replace('required_', ''))
            attr_name = self.conditions_map.get(xml_value)
            return xml_value, attr_name
        else:
            #new style
            # Get first valid condition.
            for xml_attr, attr_name in self.conditions_map.iteritems():
                xml_value = self.descriptor.xml_attributes.get(xml_attr)
                if xml_value:
                    return xml_value, attr_name
            raise Exception('Error in conditional module: unknown condition "%s"'
                % xml_attr)

    def is_condition_satisfied(self):
        self.required_modules = [self.system.get_module(descriptor) for
            descriptor in self.descriptor.get_required_module_descriptors()]

        xml_value, attr_name = self._get_condition()

        if xml_value and self.required_modules:
            for module in self.required_modules:
                if not hasattr(module, attr_name):
                    raise Exception('Error in conditional module: \
                    required module {module} has no {module_attr}'.format(
                        module=module, module_attr=attr_name))

                attr = getattr(module, attr_name)
                if callable(attr):
                    attr = attr()

                if xml_value != str(attr):
                    break
            else:
                return True
        return False

    def get_html(self):
        # Calculate html ids of dependencies
        self.required_html_ids = [descriptor.location.html_id() for
            descriptor in self.descriptor.get_required_module_descriptors()]

        return self.system.render_template('conditional_ajax.html', {
            'element_id': self.location.html_id(),
            'id': self.id,
            'ajax_url': self.system.ajax_url,
            'depends': ';'.join(self.required_html_ids)
        })

    def handle_ajax(self, dispatch, post):
        """This is called by courseware.moduleodule_render, to handle
        an AJAX call.
        """
        if not self.is_condition_satisfied():
            message = self.descriptor.xml_attributes.get('message')
            context = {'module': self,
                       'message': message}
            html = self.system.render_template('conditional_module.html',
                context)
            return json.dumps({'html': [html], 'message': bool(message)})

        html = [child.get_html() for child in self.get_display_items()]

        return json.dumps({'html': html})

    def get_icon_class(self):
        new_class = 'other'
        if self.is_condition_satisfied():
            # HACK: This shouldn't be hard-coded to two types
            # OBSOLETE: This obsoletes 'type'
            class_priority = ['video', 'problem']

            child_classes = [self.system.get_module(child_descriptor).get_icon_class()
                        for child_descriptor in self.descriptor.get_children()]
            for c in class_priority:
                if c in child_classes:
                    new_class = c
        return new_class

class ConditionalDescriptor(SequenceDescriptor):
    module_class = ConditionalModule

    filename_extension = "xml"

    stores_state = True
    has_score = False

    def __init__(self, *args, **kwargs):
        super(ConditionalDescriptor, self).__init__(*args, **kwargs)
        if self.metadata.get('required'):
            required_module_list = [tuple(x.split('/', 1)) for x in self.metadata.get('required', '').split('&')]
            self.required_module_locations = []
            for rm in required_module_list:
                try:
                    (tag, name) = rm
                except Exception as err:
                    msg = "Specification of required module in conditional is broken: %s" % self.metadata.get('required')
                    log.warning(msg)
                    self.system.error_tracker(msg)
                    continue
                loc = self.location.dict()
                loc['category'] = tag
                loc['name'] = name
                self.required_module_locations.append(Location(loc))
            log.debug('ConditionalDescriptor required_module_locations=%s' % self.required_module_locations)


    @staticmethod
    def parse_sources(xml_element, system, return_descriptor=False):
        """Parse xml_element 'sources' attr and:
        if return_descriptor=True - return list of descriptors
        if return_descriptor=False - return list of locations
        """
        result = []
        sources = xml_element.get('sources')
        if sources:
            locations = [location.strip() for location in sources.split(';')]
            for location in locations:
                if Location.is_valid(location):  # Check valid location url.
                    try:
                        if return_descriptor:
                            descriptor = system.load_item(location)
                            result.append(descriptor)
                        else:
                            result.append(location)
                    except ItemNotFoundError:
                        msg = "Invalid module by location."
                        log.exception(msg)
                        system.error_tracker(msg)
        return result

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        children = []
        show_tag_list = []
        # import ipdb; ipdb.set_trace()
        if xml_object.get('required'):
            # old syntax
            for child in xml_object:
                try:
                    descriptor = system.process_xml(etree.tostring(child))
                    module_url = descriptor.location.url()
                    children.append(module_url)
                except:
                    msg = "Unable to load child when parsing Conditional."
                    log.exception(msg)
                    system.error_tracker(msg)
            return {'show_tag_list': show_tag_list, 'children': children}
        else:  # new syntax
            for child in xml_object:
                if child.tag == 'show':
                    location = ConditionalDescriptor.parse_sources(
                        child, system)
                    children.extend(location)
                    show_tag_list.extend(location)
                else:
                    try:
                        descriptor = system.process_xml(etree.tostring(child))
                        module_url = descriptor.location.url()
                        children.append(module_url)
                    except:
                        msg = "Unable to load child when parsing Conditional."
                        log.exception(msg)
                        system.error_tracker(msg)
            return {'show_tag_list': show_tag_list, 'children': children}

    def definition_to_xml(self, resource_fs):
        xml_object = etree.Element(self._tag_name)
        for child in self.get_children():
            location = str(child.location)
            if location in self.show_tag_list:
                show_str = '<{tag_name} sources="{sources}" />'.format(
                    tag_name='show', sources=location)
                xml_object.append(etree.fromstring(show_str))
            else:
                xml_object.append(
                    etree.fromstring(child.export_to_xml(resource_fs)))
        return xml_object

    def get_required_module_descriptors(self):
        """Returns a list of XModuleDescritpor instances upon
        which this module depends.
        """
        if self.metadata.get('required'):
            return [self.system.load_item(loc) for loc in self.required_module_locations]
        else:
            return ConditionalDescriptor.parse_sources(
                self.xml_attributes, self.system, True)
