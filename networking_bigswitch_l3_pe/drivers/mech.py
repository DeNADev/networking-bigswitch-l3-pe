# Copyright 2016 DeNA Co., Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import bsnstacklib.plugins.bigswitch.config
import logging
from neutron import context as ncontext
from neutron.db import db_base_plugin_v2
from neutron.plugins.ml2.driver_api import MechanismDriver
import networking_bigswitch_l3_pe.lib.config
from networking_bigswitch_l3_pe.lib.exceptions import UpdateNetworkNameError
from networking_bigswitch_l3_pe.lib.keystone_client import KeystoneClient
from networking_bigswitch_l3_pe.lib.rest_client import RestClient
from oslo_config import cfg
LOG = logging.getLogger(__name__)


class BCFPhysicalEditionMechanismDriver(MechanismDriver):

    def __init__(self):
        bsnstacklib.plugins.bigswitch.config.register_config()
        networking_bigswitch_l3_pe.lib.config.register_config()

        api_url = cfg.CONF.networking_bigswitch_l3_pe.api_url
        username, password = cfg.CONF.RESTPROXY.server_auth.split(':')
        self.neutron_id = cfg.CONF.RESTPROXY.neutron_id

        self.client = RestClient(api_url, username, password)
        self.keystone_client = KeystoneClient()
        self.db_plugin = db_base_plugin_v2.NeutronDbPluginV2()

    def initialize(self):
        pass

    def create_network_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = context.current['name']
        self.client.create_net(project_name, segment_name)

    def update_network_precommit(self, context):
        self._validate_network_update(context)

    def delete_network_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = context.current['name']
        self.client.delete_net(project_name, segment_name)

    def create_subnet_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = self._get_segment_name(context.current['network_id'])
        gateway_ip = self._get_gateway_ip(context.current)
        if gateway_ip:
            self.client.create_subnet(project_name, segment_name, gateway_ip)
        else:
            LOG.debug("gateway_ip is not defined in segment(%(segment_name)s)"
                      " of tenant(%(tenant_name)s)",
                      {'tenant_name': project_name,
                       'segment_name': segment_name})

    def update_subnet_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = self._get_segment_name(context.current['network_id'])
        current_gateway_ip = self._get_gateway_ip(context.current)
        original_gateway_ip = self._get_gateway_ip(context.original)
        if current_gateway_ip == original_gateway_ip:
            return
        if current_gateway_ip:
            self.client.update_subnet(project_name, segment_name,
                                      original_gateway_ip, current_gateway_ip)
        else:
            self.client.delete_subnet(project_name, segment_name,
                                      original_gateway_ip)

    def delete_subnet_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = self._get_segment_name(context.current['network_id'])
        gateway_ip = self._get_gateway_ip(context.current)
        if gateway_ip:
            self.client.delete_subnet(project_name, segment_name, gateway_ip)
        else:
            LOG.debug("gateway_ip is not defined in segment(%(segment_name)s)"
                      " of tenant(%(tenant_name)s)",
                      {'tenant_name': project_name,
                       'segment_name': segment_name})

    def _get_project_name(self, tenant_id):
        projects = self.keystone_client.get_projects()
        LOG.debug("project: id=%(project_id)s, name=%(name)s",
                  {'project_id': tenant_id, 'name': projects[tenant_id]})
        return projects[tenant_id] + "." + self.neutron_id

    def _get_segment_name(self, network_id):
        ctx = ncontext.get_admin_context()
        net = self.db_plugin.get_network(ctx, network_id)
        LOG.debug("network: id=%(network_id)s, name=%(name)s",
                  {'network_id': network_id, 'name': net['name']})
        return net['name']

    def _get_gateway_ip(self, current):
        if current['gateway_ip']:
            return current['gateway_ip'] + '/' + current['cidr'].split('/')[1]
        else:
            return None

    def _validate_network_update(self, context):
        if context.current['name'] != context.original['name']:
            raise UpdateNetworkNameError()
