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
from networking_bigswitch_l3_pe.lib.keystone_client import KeystoneClient
from networking_bigswitch_l3_pe.lib.rest_client import RestClient
from neutron.common import exceptions
from neutron import context as ncontext
from neutron.db import db_base_plugin_v2
from neutron.plugins.ml2 import models
import time

LOG = logging.getLogger(__name__)


class Synchronizer(object):
    def __init__(self, api_url, username, password, neutron_id,
                 exclude_physical_networks, dry_run=False):
        self.rest_client = RestClient(api_url, username, password)
        self.keystone_client = KeystoneClient()
        self.db_plugin = db_base_plugin_v2.NeutronDbPluginV2()
        self.neutron_id = neutron_id
        self.exclude_physical_networks = exclude_physical_networks
        self.dry_run = dry_run
        if self.dry_run:
            LOG.info("This is dry run mode.")
        self.rest_sleep = 0.5

    def _get_os_projects(self):
        return self.keystone_client.get_projects()

    def _get_exclude_networks(self):
        ctx = ncontext.get_admin_context()
        with ctx.session.begin(subtransactions=True):
            query = (ctx.session.query(models.NetworkSegment).
                     order_by(models.NetworkSegment.segment_index))
            records = query.all()

            return [r.network_id for r in records
                    if r.physical_network in self.exclude_physical_networks]

    def _get_os_networks(self):
        ctx = ncontext.get_admin_context()
        ret = self.db_plugin.get_networks(ctx)
        return ret

    def _get_os_subnets(self):
        ctx = ncontext.get_admin_context()
        return self.db_plugin.get_subnets(ctx)

    def _exist_subnet(self, os, subnet, ip_cidr):
        for s in os['subnets']:
            gateway_ip = self._get_gateway_ip(s)
            if s['id'] != subnet['id'] and \
               s['tenant_id'] == subnet['tenant_id'] and \
               s['network_id'] == subnet['network_id'] and \
               gateway_ip == ip_cidr:
                return s
        return None

    def _check_network_in_bcf(self, bcf, tenant_name, network_name):
        matches = [t for t in bcf['tenants'] if t['name'] == tenant_name]
        for m in matches:
            if 'logical-router' in m and \
               'tenant-interface' in m['logical-router'] and \
               'segment-interface' in m['logical-router']:
                for si in m['logical-router']['segment-interface']:
                    if si['segment'] == network_name:
                        return None
        return {
            'project_name': tenant_name,
            'segment_name': network_name,
        }

    def _check_subnet_in_bcf(self, bcf, os,
                             tenant_name, network_name, subnet):
        gateway_ip = self._get_gateway_ip(subnet)
        matches = [t for t in bcf['tenants'] if t['name'] == tenant_name]
        for m in matches:
            if not ('logical-router' in m and
                    'tenant-interface' in m['logical-router'] and
                    'segment-interface' in m['logical-router']):
                continue

            for si in m['logical-router']['segment-interface']:
                if not (si['segment'] == network_name and
                        'ip-subnet' in si):
                    continue

                for i in si['ip-subnet']:
                    if 'ip-cidr' not in i:
                        continue
                    if i['ip-cidr'] == gateway_ip:
                        # no change
                        return None
                    else:
                        if not self._exist_subnet(os, subnet,
                                                  i['ip-cidr']):
                            # update subnet
                            return {
                                'project_name': tenant_name,
                                'segment_name': network_name,
                                'original_gateway_ip': i['ip-cidr'],
                                'current_gateway_ip': gateway_ip,
                            }
        # add subnet
        return {
            'project_name': tenant_name,
            'segment_name': network_name,
            'current_gateway_ip': gateway_ip,
        }

    def _add_networks_to_bcf(self, networks):
        if len(networks) > 0:
            LOG.info("Adding networks: %(networks)s",
                     {'networks': networks})
        if self.dry_run:
            return networks

        ret = []
        for n in networks:
            if self.rest_client.create_net(n['project_name'],
                                           n['segment_name']):
                ret.append(n)
            time.sleep(self.rest_sleep)

        return ret

    def _add_subnets_to_bcf(self, subnets):
        if len(subnets) > 0:
            LOG.info("Adding subnets: %(subnets)s",
                     {'subnets': subnets})
        if self.dry_run:
            return subnets

        ret = []
        for s in subnets:
            if ('original_gateway_ip' in s):
                if self.rest_client.update_subnet(s['project_name'],
                                                  s['segment_name'],
                                                  s['original_gateway_ip'],
                                                  s['current_gateway_ip']):
                    ret.append(s)
            else:
                if self.rest_client.create_subnet(s['project_name'],
                                                  s['segment_name'],
                                                  s['current_gateway_ip']):
                    ret.append(s)
            time.sleep(self.rest_sleep)
        return ret

    def _delete_subnets_in_bcf(self, subnets):
        if len(subnets) > 0:
            LOG.info("Deleting subnets: %(subnets)s",
                     {'subnets': subnets})
        if self.dry_run:
            return subnets

        ret = []
        for s in subnets:
            if self.rest_client.delete_subnet(s['project_name'],
                                              s['segment_name'],
                                              s['current_gateway_ip']):
                ret.append(s)
            time.sleep(self.rest_sleep)
        return ret

    def _delete_networks_in_bcf(self, networks):
        if len(networks) > 0:
            LOG.info("Deleting networks: %(networks)s",
                     {'networks': networks})
        if self.dry_run:
            return networks

        ret = []
        for n in networks:
            if self.rest_client.delete_net(n['project_name'],
                                           n['segment_name']):
                ret.append(n)
            time.sleep(self.rest_sleep)

        return ret

    def _delete_system_tenant_interfaces(self, interfaces):
        if len(interfaces) > 0:
            LOG.info("Deleting system tenant interfaces: %(interfaces)s",
                     {'interfaces': interfaces})
        if self.dry_run:
            return interfaces

        ret = []
        for i in interfaces:
            if self.rest_client.delete_system_tenant_interface(i):
                ret.append(i)
            time.sleep(self.rest_sleep)
        return ret

    def _find_project_in_os(self, os, tenant_name):
        return next((p for p in os['projects']
                     if (self._get_tenant_name(os, p)) ==
                     tenant_name), None)

    def _find_subnets_in_os(self, os, ip_cidr):
        return [s for s in os['subnets'] if self._get_gateway_ip(s) == ip_cidr]

    def _find_networks_in_os(self, os, segment_name):
        return [n for n in os['networks'] if n['name'] == segment_name]

    def _check_subnet_in_os(self, os, tenant):
        ret = []
        for si in tenant['logical-router']['segment-interface']:
            if 'ip-subnet' not in si:
                continue

            for i in si['ip-subnet']:
                if 'ip-cidr' not in i:
                    continue

                if self._find_subnets_in_os(os, i['ip-cidr']):
                    continue

                ret.append({
                    'project_name': tenant['name'],
                    'segment_name': si['segment'],
                    'current_gateway_ip': i['ip-cidr'],
                })

        return ret

    def _check_network_in_os(self, os, tenant):
        ret = []
        for si in tenant['logical-router']['segment-interface']:
            if self._find_networks_in_os(os, si['segment']):
                continue

            ret.append({
                'project_name': tenant['name'],
                'segment_name': si['segment'],
            })

        return ret

    def _get_gateway_ip(self, subnet):
        if ('gateway_ip' not in subnet) or (not subnet['gateway_ip']):
            emsg = "subnet(%(subnet_id)s) doensn't have gateway_ip" % {
                   'subnet_id': subnet['id']}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

        if ('cidr' not in subnet) or (not subnet['cidr']):
            emsg = "subnet(%(subnet_id)s) doensn't have cidr" % {
                   'subnet_id': subnet['id']}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

        ip, mask = subnet['cidr'].split('/')
        if not mask:
            emsg = "cidr(%(cidr)s) of subnet(%(subnet_id)s)" \
                   " is wrong format" % {
                       'cidr': subnet['cidr'],
                       'subnet_id': subnet['id']}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

        return subnet['gateway_ip'] + '/' + mask

    def _get_tenant_name(self, os, tenant_id):
        if tenant_id not in os['projects']:
            emsg = "tenant(%(tenant_id)s) is not found" % {
                   'tenant_id': tenant_id}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

        if not os['projects'][tenant_id]:
            emsg = "tenant name(%(tenant_id)s) is empty" % {
                   'tenant_id': tenant_id}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

        return os['projects'][tenant_id] + '.' + self.neutron_id

    def _get_tenant_id(self, os, tenant_id):
        if tenant_id not in os['projects']:
            emsg = "tenant(%(tenant_id)s) is not found" % {
                   'tenant_id': tenant_id}
            LOG.debug(emsg)
            raise exceptions.Invalid(error_message=emsg)

        if not os['projects'][tenant_id]:
            emsg = "tenant name(%(tenant_id)s) is empty" % {
                   'tenant_id': tenant_id}
            LOG.debug(emsg)
            raise exceptions.Invalid(error_message=emsg)

        return os['projects'][tenant_id] + '.' + self.neutron_id

    def _get_network(self, os, network_id):
        network = next((n for n in os['networks']
                        if n['id'] == network_id), None)
        if network:
            return network
        else:
            emsg = "network(%(network_id)s) is not found" % {
                   'network_id': network_id}
            LOG.debug(emsg)
            raise exceptions.Invalid(message=emsg)

    def _add_resources(self, os, bcf):
        networks = []
        for n in os['networks']:
            tenant_name = self._get_tenant_name(os, n['tenant_id'])
            ret = self._check_network_in_bcf(bcf, tenant_name, n['name'])
            if ret:
                networks.append(ret)

        subnets = []
        for s in os['subnets']:
            tenant_name = self._get_tenant_name(os, s['tenant_id'])
            network = self._get_network(os, s['network_id'])
            ret = self._check_subnet_in_bcf(bcf, os, tenant_name,
                                            network['name'], s)
            if ret:
                subnets.append(ret)

        networks = self._add_networks_to_bcf(networks)
        subnets = self._add_subnets_to_bcf(subnets)

        ret = {}
        if len(networks) > 0:
            ret['network'] = networks
        if len(subnets) > 0:
            ret['subnet'] = subnets
        return ret

    def _check_project_in_os(self, os, bcf, tenant_name):
        project = self._find_project_in_os(os, tenant_name)
        if project:
            return None

        # Check if the tenant doesn't exist in BCF.
        tenant = next((t for t in bcf['tenants']
                       if t['name'] == tenant_name), None)
        if tenant:
            LOG.debug("tenant(%(tenant)s) still exists in BCF. "
                      "skip to delete the system tenant interface.",
                      {'tenant': tenant_name})
            return None

        return tenant_name

    def _filter_by_events(self, events, resources):
        ret = []
        for r in resources:
            if next((e for e in events if e['payload'] == r), None):
                ret.append(r)
            else:
                LOG.warn("There were no operations to delete it. "
                         "Please delete it manually: %(resource)s.",
                         {'resource': r})
        return ret

    def _delete_resources(self, bcf, os, events):
        subnets = []
        networks = []
        for t in bcf['tenants']:
            if not ('logical-router' in t and
                    'tenant-interface' in t['logical-router'] and
                    'segment-interface' in t['logical-router']):
                continue

            ret = self._check_subnet_in_os(os, t)
            if ret:
                subnets.extend(ret)

            ret = self._check_network_in_os(os, t)
            if ret:
                networks.extend(ret)

        if not (events is None):
            # Delete only networks/subnets which were deleted by users.
            subnets = self._filter_by_events(events, subnets)
            networks = self._filter_by_events(events, networks)

        subnets = self._delete_subnets_in_bcf(subnets)
        networks = self._delete_networks_in_bcf(networks)

        ret = {}
        if len(subnets) > 0:
            ret['subnets'] = subnets
        if len(networks) > 0:
            ret['networks'] = networks
        return ret

    def _get_bcf_resources(self):
        tenants = self.rest_client.get_tenants(self.neutron_id)
        system_tenant_interfaces =\
            self.rest_client.get_system_tenant_interfaces(self.neutron_id)
        return {
            'tenants': tenants,
            'system_tenant_interfaces': system_tenant_interfaces,
        }

    def _get_os_resources(self):
        projects = self._get_os_projects()
        networks = self._get_os_networks()
        subnets = self._get_os_subnets()

        exclude_networks = self._get_exclude_networks()
        LOG.debug("exclude_networks=%(exclude_networks)s",
                  {'exclude_networks': exclude_networks})
        networks = [n for n in networks
                    if n['id'] not in exclude_networks]
        subnets = [s for s in subnets
                   if s['network_id'] not in exclude_networks]

        return {
            'projects': projects,
            'networks': networks,
            'subnets': subnets,
        }

    def synchronize(self, events=None):
        LOG.info("Start synchronization: events=%(events)s",
                 {'events': events})

        self.rest_client.renew_session()

        bcf = self._get_bcf_resources()
        os = self._get_os_resources()

        ret = {}
        added = self._add_resources(os, bcf)
        deleted = self._delete_resources(bcf, os, events)

        if len(added) > 0:
            ret['added'] = added
        if len(deleted) > 0:
            ret['deleted'] = deleted
        if ret:
            LOG.info("Finished synchronization%(dry_run)s: "
                     "synchronized resources: %(resource)s.",
                     {'resource': ret,
                      'dry_run': '(dry run mode)' if self.dry_run else ''})
        else:
            LOG.info("Finished synchronization%(dry_run)s: "
                     "Already synchronized.",
                     {'dry_run': '(dry run mode)' if self.dry_run else ''})
        return ret
