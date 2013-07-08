import json
import logging
import urllib

from pkg_resources import resource_string

from xmodule.x_module import XModule
from xmodule.xml_module import XmlDescriptor
from xmodule.raw_module import RawDescriptor
from xmodule.editing_module import MetadataOnlyEditingDescriptor

from xblock.core import Scope, String, Boolean


log = logging.getLogger(__name__)

DEFAULT_CODE = ' '


class PythonTutorFields(object):
    code = String(
        help="The code",
        scope=Scope.settings,
        default=DEFAULT_CODE
    )

    vertical = Boolean(
        help="Display vertically",
        scope=Scope.settings,
        default=False
    )


class PythonTutorModule(PythonTutorFields, XModule):
    css = {}
    js = {
        'coffee': [],
        'js': []
    }

    def __init__(self, *args, **kwargs):
        XModule.__init__(self, *args, **kwargs)

    def get_html(self):
        code = self.code
        context = {
            'raw_code': code,
            'urlencoded_code': urllib.quote(code),
            'vertical': 'true' if self.vertical else 'false',
        }

        html = self.system.render_template('pythontutor.html', context)
        return html


class PythonTutorDescriptor(MetadataOnlyEditingDescriptor,
                            RawDescriptor,
                            PythonTutorFields):
    module_class = PythonTutorModule
    template_dir_name = "pythontutor"

    @classmethod
    def definition_from_xml(cls, xml_object, system):
        code = xml_object.text
        code = code.strip() if code else DEFAULT_CODE

        vertical = xml_object.get('vertical_stack')

        definition = {
            'code': code,
            'vertical': vertical,
        }

        children = None

        return definition, children

    def definition_to_xml(self, fs):
        raise NotImplementedError
