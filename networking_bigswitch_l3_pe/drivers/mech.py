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

try:
    import networking_bigswitch.plugins.bigswitch.config as bigswitch_config
except ImportError:
    import bsnstacklib.plugins.bigswitch.config as bigswitch_config
import eventlet
import logging
import networking_bigswitch_l3_pe.lib.config
from networking_bigswitch_l3_pe.lib.event import EVENT_NETWORK_DELETE
from networking_bigswitch_l3_pe.lib.event import EVENT_SUBNET_DELETE
from networking_bigswitch_l3_pe.lib.event import EventNotifier
from networking_bigswitch_l3_pe.lib.event import EventWatcher
from networking_bigswitch_l3_pe.lib.keystone_client import KeystoneClient
from networking_bigswitch_l3_pe.lib.synchronizer import Synchronizer
from neutron import context as ncontext
from neutron.db import db_base_plugin_v2
from neutron.plugins.ml2.driver_api import MechanismDriver
from oslo_config import cfg

LOG = logging.getLogger(__name__)


class BCFPhysicalEditionMechanismDriver(MechanismDriver):

    def __init__(self):
        bigswitch_config.register_config()
        networking_bigswitch_l3_pe.lib.config.register_config()

        api_url = cfg.CONF.networking_bigswitch_l3_pe.api_url
        username, password = cfg.CONF.RESTPROXY.server_auth.split(':')
        self.neutron_id = cfg.CONF.RESTPROXY.neutron_id
        exclude_physical_networks = \
            cfg.CONF.networking_bigswitch_l3_pe.exclude_physical_networks
        self.sync = Synchronizer(api_url, username, password, self.neutron_id,
                                 exclude_physical_networks)
        self.notifier = EventNotifier()
        self.watcher = EventWatcher()
        self.keystone_client = KeystoneClient()
        self.db_plugin = db_base_plugin_v2.NeutronDbPluginV2()

        eventlet.spawn(self.watcher.watch)
        eventlet.spawn(self._bcf_sync,
                       cfg.CONF.networking_bigswitch_l3_pe.sync_interval)

    def _bcf_sync(self, polling_interval=600):
        while True:
            try:
                eventlet.sleep(polling_interval)
                events = self.watcher.pop_events()
                self.sync.synchronize(events=events)
            except Exception as e:
                LOG.exception("Excpetion in _bcf_sync: %(e)s", {'e': e})

    def initialize(self):
        pass

    def delete_network_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = context.current['name']
        self.notifier.notify(context.current, EVENT_NETWORK_DELETE, {
            'project_name': project_name,
            'segment_name': segment_name,
        })

    def delete_subnet_postcommit(self, context):
        project_name = self._get_project_name(context.current['tenant_id'])
        segment_name = self._get_segment_name(context.current['network_id'])
        gateway_ip = self._get_gateway_ip(context.current)
        self.notifier.notify(context.current, EVENT_SUBNET_DELETE, {
            'project_name': project_name,
            'segment_name': segment_name,
            'current_gateway_ip': gateway_ip,
        })

    def _get_project_name(self, tenant_id):
        projects = self.keystone_client.get_projects()
        return projects[tenant_id] + "." + self.neutron_id

    def _get_segment_name(self, network_id):
        ctx = ncontext.get_admin_context()
        net = self.db_plugin.get_network(ctx, network_id)
        return net['name']

    def _get_gateway_ip(self, current):
        if current['gateway_ip']:
            return current['gateway_ip'] + '/' + current['cidr'].split('/')[1]
        else:
            return None
