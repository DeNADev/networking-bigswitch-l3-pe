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
import eventlet
from neutron.plugins.ml2.driver_api import MechanismDriver
import networking_bigswitch_l3_pe.lib.config
from networking_bigswitch_l3_pe.lib.synchronizer import Synchronizer
from oslo_config import cfg
LOG = logging.getLogger(__name__)


class BCFPhysicalEditionMechanismDriver(MechanismDriver):

    def __init__(self):
        bsnstacklib.plugins.bigswitch.config.register_config()
        networking_bigswitch_l3_pe.lib.config.register_config()

        api_url = cfg.CONF.networking_bigswitch_l3_pe.api_url
        username, password = cfg.CONF.RESTPROXY.server_auth.split(':')
        neutron_id = cfg.CONF.RESTPROXY.neutron_id
        self.sync = Synchronizer(api_url, username, password, neutron_id)

        eventlet.spawn(self._bcf_sync,
                       cfg.CONF.networking_bigswitch_l3_pe.sync_interval)

    def _bcf_sync(self, polling_interval=600):
        while True:
            try:
                eventlet.sleep(polling_interval)
                self.sync.synchronize()
            except Exception as e:
                LOG.exception("Excpetion in _bcf_sync: %(e)s", {'e': e})

    def initialize(self):
        pass
