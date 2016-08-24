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

from keystoneclient.v2_0 import client as clientv2
import logging
from oslo_config import cfg
from six.moves.urllib import parse
LOG = logging.getLogger(__name__)


class KeystoneClient(object):
    def __init__(self):
        auth_url = cfg.CONF.keystone_authtoken.auth_uri
        auth_user = cfg.CONF.keystone_authtoken.admin_user
        auth_password = cfg.CONF.keystone_authtoken.admin_password
        auth_tenant = cfg.CONF.keystone_authtoken.admin_tenant_name
        self.version = self._get_api_version(auth_url)
        if self.version == 'v2':
            LOG.debug("auth_url=%(auth_url)s, auth_user=%(auth_user)s, "
                      "auth_tenant=%(auth_tenant)s",
                      {'auth_url': auth_url, 'auth_user': auth_user,
                       'auth_tenant': auth_tenant})
            self.keystone_client = clientv2.Client(
                auth_url=auth_url,
                username=auth_user,
                password=auth_password,
                tenant_name=auth_tenant,
            )
        elif self.version == 'v3':
            cfg.Error('keystone api v3 is not supported yet')

    def _get_api_version(self, auth_url):
        path = parse.urlparse(auth_url).path
        if '/v3' in path:
            return 'v3'
        else:
            return 'v2'

    def get_projects(self):
        if self.version == 'v2':
            projects = self.keystone_client.tenants.list()
        elif self.version == 'v3':
            cfg.Error('keystone api v3 is not supported yet')
        return {p.id: p.name for p in projects}
