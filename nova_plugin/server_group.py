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


import copy
from cloudify import ctx
from cloudify.decorators import operation
from openstack_plugin_common import (
    with_nova_client,
    use_external_resource,
    OPENSTACK_ID_PROPERTY,
    OPENSTACK_TYPE_PROPERTY,
    OPENSTACK_NAME_PROPERTY)


SERVER_GROUP_OPENSTACK_TYPE = 'server_group'

@operation
@with_nova_client
def create(nova_client, args, **kwargs):
    external_group = use_external_resource(ctx, nova_client,
                                           SERVER_GROUP_OPENSTACK_TYPE)
    if external_group:
        return

    ctx.logger.info('Creating server group: args={0}'.format(args))
    nova_client.client.authenticate()
    tenant_id = nova_client.client.service_catalog.get_tenant_id()
    sg_request = {'tenant_id': tenant_id}
    sg_request.update(copy.deepcopy(args))

    ctx.logger.debug('Sending request for creating server group: sg_request={0}'.format(sg_request))
    sg_response = nova_client.server_groups.create(**sg_request)
    ctx.logger.debug('sg_response={0}'.format(sg_response))
    ctx.logger.info('Server group created')

    sg_id = sg_response['server_group']['id']
    sg_name = sg_response['server_group']['name']

    ctx.instance.runtime_properties['sg.id'] = sg_id
    # Cache so we save the authenticate() roundtrip from later
    ctx.instance.runtime_properties['sg.tenant_id'] = tenant_id

    ctx.instance.runtime_properties[OPENSTACK_ID_PROPERTY] = sg_id
    ctx.instance.runtime_properties[OPENSTACK_TYPE_PROPERTY] = \
        SERVER_GROUP_OPENSTACK_TYPE
    ctx.instance.runtime_properties[OPENSTACK_NAME_PROPERTY] = sg_name


@operation
@with_nova_client
def delete(nova_client, args, **kwargs):
    rt_props = ctx.instance.runtime_properties
    sg_id = rt_props['sg.id']
    sg_tenant_id = rt_props['sg.tenant_id']

    sg_request = {'tenant_id': sg_tenant_id,
                  'ServerGroup_id': sg_id}
    sg_request.update(copy.deepcopy(args))

    ctx.logger.debug('Sending request for deleting server group: sg_request={0}'.format(sg_request))
    nova_client.server_groups.delete(**sg_request)
    ctx.logger.info('Server group deleted')
