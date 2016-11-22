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

import logging
from oslo_config import cfg
import oslo_messaging

LOG = logging.getLogger(__name__)

OSLO_TOPIC = 'networking_bigswitch_l3_pe'
OSLO_NAMESPACE = 'networking_bigswitch_l3_pe'
EVENT_NETWORK_DELETE = 'delete_network'
EVENT_SUBNET_DELETE = 'delete_subnet'


class EventWatcherEndpoint(object):
    target = oslo_messaging.Target(namespace=OSLO_NAMESPACE)

    def __init__(self, watcher):
        self.watcher = watcher

    def info(self, ctxt, event_type, payload):
        event = {
            'event_type': event_type,
            'payload': payload,
        }
        self.watcher.events.append(event)
        LOG.debug('recieved event: event_type=%(event_type)s, '
                  'payload=%(payload)s, ctxt=%(ctxt)s',
                  {'event_type': event_type,
                   'payload': payload,
                   'ctxt': ctxt})


class EventWatcher(object):
    def __init__(self):
        self.events = []

        transport = oslo_messaging.get_transport(cfg.CONF)
        target = oslo_messaging.Target(topic=OSLO_TOPIC, server=cfg.CONF.host)
        endpoints = [EventWatcherEndpoint(self)]
        self.server = oslo_messaging.get_rpc_server(transport,
                                                    target,
                                                    endpoints)

    def watch(self):
        LOG.debug('start EventWatcher.watch()')
        self.server.start()
        self.server.wait()

    def pop_events(self):
        ret = self.events
        self.events = []
        return ret


class EventNotifier(object):
    def __init__(self):
        transport = oslo_messaging.get_transport(cfg.CONF)
        target = oslo_messaging.Target(topic=OSLO_TOPIC)
        self.client = oslo_messaging.RPCClient(transport, target)

    def notify(self, context, event_type, event):
        cctxt = self.client.prepare(namespace=OSLO_NAMESPACE)
        cctxt.cast(context, 'info', event_type=event_type, payload=event)
        LOG.debug('notified event: event_type=%(event_type)s, event=%(event)s',
                  {'event_type': event_type,
                   'event': event})
