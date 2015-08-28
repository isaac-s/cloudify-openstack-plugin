#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import uuid
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from cloudify import exceptions
from cloudify import ctx


def handle_userdata(server):

    existing_userdata = server.get('userdata')

    if (ctx.node.properties.get('install_agent') and
            ctx.node.properties.get('remote_execution') is False):
        install_agent_userdata = ctx.agent.init_script()
    else:
        install_agent_userdata = None

    if not (existing_userdata or install_agent_userdata):
        return

    if isinstance(existing_userdata, dict):
        ud_type = existing_userdata['type']
        if ud_type not in userdata_handlers:
            raise exceptions.NonRecoverableError(
                "Invalid type '{0}' for server userdata)".format(ud_type))
        existing_userdata = userdata_handlers[ud_type](existing_userdata)

    if not existing_userdata:
        final_userdata = install_agent_userdata
    elif not install_agent_userdata:
        final_userdata = existing_userdata
    else:
        final_userdata = _create_multi_mimetype_userdata(
            [existing_userdata, install_agent_userdata])
    server['userdata'] = final_userdata


SCRIPT_MIME_TYPE = 'text/x-shellscript'
mapping_prefixes = {
    '#include': 'text/x-include-url',
    '#include-once': 'text/x-include-once-url',
    '#cloud-config': 'text/cloud-config',
    '#cloud-config-archive': 'text/cloud-config-archive',
    '#upstart-job': 'text/upstart-job',
    '#part-handler': 'text/part-handler',
    '#cloud-boothook': 'text/cloud-boothook',
    '#!': SCRIPT_MIME_TYPE,
    'rem cmd': SCRIPT_MIME_TYPE,
    '#ps1_sysnative': SCRIPT_MIME_TYPE,
    '#ps1_x86': SCRIPT_MIME_TYPE
}

script_extensions = {
    '#!': 'sh',
    'rem cmd': 'cmd',
    '#ps1_sysnative': 'ps1',
    '#ps1_x86': 'ps1'
}


def _find_type(line):
    sorted_prefixes = sorted(mapping_prefixes, key=lambda e: -len(e))
    for possible_prefix in sorted_prefixes:
        if line.startswith(possible_prefix):
            return mapping_prefixes[possible_prefix]
    raise exceptions.NonRecoverableError(
        'Unhandled userdata that starts with: {0}'.format(line))


def _find_extension(line):
    sorted_prefixes = sorted(script_extensions, key=lambda e: -len(e))
    for possible_prefix in sorted_prefixes:
        if line.startswith(possible_prefix):
            return script_extensions[possible_prefix]
    return None


def _create_multi_mimetype_userdata(userdatas):
    outer = MIMEMultipart()
    for userdata in userdatas:
        parsed = email.message_from_string(userdata)
        if parsed.is_multipart():
            for msg in parsed.walk():
                if msg.get_content_maintype().lower() != 'multipart':
                    outer.attach(msg)
        else:
            first_line = userdata.split('\n')[0]
            mtype = _find_type(first_line)
            # extension is required by older versions of cloudbase-init
            # to select the proper shell
            extension = _find_extension(first_line)
            _, subtype = mtype.split('/', 1)
            msg = MIMEText(userdata, _subtype=subtype)
            suffix = ''
            if extension:
                suffix = '.{0}'.format(extension)
            filename = '{0}{1}'.format(uuid.uuid4(), suffix)
            msg.add_header('Content-Disposition', 'attachment',
                           filename=filename)
            outer.attach(msg)
    # cloudbase-init doesn't handle the From prefix well
    return outer.as_string(unixfrom=False)


userdata_handlers = {
    'http': lambda params: requests.get(params['url']).text
}
