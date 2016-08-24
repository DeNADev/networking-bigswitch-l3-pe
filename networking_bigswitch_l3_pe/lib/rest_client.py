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

import json
import logging
from neutron.common import exceptions
from networking_bigswitch_l3_pe.lib.exceptions import BCFRestError
import urllib
import urllib2
LOG = logging.getLogger(__name__)

BASE_PATH = '/data/controller/applications/bcf'
TENANT_IF_PATH =\
    BASE_PATH +\
    '/tenant[name="{tenant}"]/logical-router' +\
    '/tenant-interface[remote-tenant="{remote}"]'
STATIC_ROUTE_PATH =\
    BASE_PATH +\
    '/tenant[name="{tenant}"]/logical-router' +\
    '/static-route[dst-ip-subnet="0.0.0.0/0"]'
SEGMENT_IFS_PATH =\
    BASE_PATH +\
    '/tenant[name="{tenant}"]/logical-router' +\
    '/segment-interface'
SEGMENT_IF_PATH =\
    SEGMENT_IFS_PATH + '[segment="{segment}"]'
IP_CIDR_PATH =\
    BASE_PATH +\
    '/tenant[name="{tenant}"]/logical-router' +\
    '/segment-interface[segment="{segment}"]' +\
    '/ip-subnet[ip-cidr="{ip_cidr}"]'
AAA_SESSION_PATH =\
    '/data/controller/core/aaa' +\
    '/session[auth-token="{session}"]'


class RestClient(object):
    def __init__(self, api_url, username, password):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.session_cookie = None

    def _renew_session(self):
        if self.session_cookie:
            self._destruct_session(self.session_cookie)

        urlLogin = self.api_url + '/auth/login'
        data1 = {"password": str(self.password), "user": str(self.username)}
        code, output = self._rest_request(str(urlLogin), json.dumps(data1),
                                          None, "POST")
        authObj = json.loads(output)
        self.session_cookie = authObj["session_cookie"]

    def _destruct_session(self, session_cookie):
        path = AAA_SESSION_PATH.format(session=session_cookie)
        try:
            code, output = self.rest_call(path, json.dumps({}), verb='DELETE')
        except urllib2.HTTPError as e:
            LOG.debug("Ignore HTTPError: %(e)s", {'e': e})
        finally:
            self.session_cookie = None

    def rest_call(self, path, data, verb='GET', param=None):
        url = self._build_url(path, param)
        return self._rest_request(url, data, self.session_cookie, verb)

    def _rest_request(self, url, data, session, verb):
        headers = {'Content-type': 'application/json'}
        if session:
            headers["Cookie"] = "session_cookie=%s" % session
        LOG.debug("verb:%(verb)s url:%(url)s "
                  "headers:%(headers)s data:%(data)s", {
                      'verb': verb, 'url': url,
                      'headers': headers, 'data': data})
        request = urllib2.Request(url, data, headers)
        request.get_method = lambda: verb
        response = urllib2.urlopen(request)
        code = response.code
        result = response.read()
        LOG.debug("code:%(code)s result:%(result)s",
                  {'code': code, 'result': result})
        if code not in range(200, 300):
            raise BCFRestError(code=code, result=result,
                               method=verb, url=url, data=data)
        return (code, result)

    def _build_url(self, path, param):
        ret = self.api_url + urllib.quote(path)
        if param:
            ret += '?' + param
        return ret

    def create_net(self, tenant_name, segment_name):
        if not (tenant_name and segment_name):
            emsg = "Invalid parameter for create_net: "\
                   "tenant_name=%(tenant_name)s, "\
                   "segment_name=%(segment_name)s" % {
                       'tenant_name': tenant_name,
                       'segment_name': segment_name}
            LOG.debug(emsg)
            raise exceptions.InvalidInput(error_message=emsg)

        self._renew_session()

        # create tenant-interface
        path = TENANT_IF_PATH.format(tenant='system',
                                     remote=tenant_name)
        self.rest_call(path, json.dumps({"remote-tenant": tenant_name}),
                       verb='PUT')

        path = TENANT_IF_PATH.format(tenant=tenant_name,
                                     remote='system')
        self.rest_call(
            path, json.dumps({"remote-tenant": "system"}), verb='PUT')

        # add static route
        path = STATIC_ROUTE_PATH.format(tenant=tenant_name)
        self.rest_call(path, json.dumps({"next-hop": {"tenant": "system"},
                       "dst-ip-subnet": "0.0.0.0/0"}), verb='PUT')

        # create segment interface
        path = SEGMENT_IF_PATH.format(tenant=tenant_name, segment=segment_name)
        self.rest_call(path, json.dumps({"segment": segment_name}), verb='PUT')

        return True

    def create_subnet(self, tenant_name, segment_name, ip_cidr):
        return self.update_subnet(tenant_name, segment_name, ip_cidr, ip_cidr)

    def update_subnet(self, tenant_name, segment_name,
                      orig_ip_cidr, current_ip_cidr):
        if not (tenant_name and segment_name and current_ip_cidr):
            emsg = "Invalid parameter for update_subnet: "\
                   "tenant_name=%(tenant_name)s, "\
                   "segment_name=%(segment_name)s, "\
                   "current_ip_cidr=%(current_ip_cidr)s" % {
                       'tenant_name': tenant_name,
                       'segment_name': segment_name,
                       'current_ip_cidr': current_ip_cidr}
            LOG.debug(emsg)
            raise exceptions.InvalidInput(error_message=emsg)

        self._renew_session()

        if not orig_ip_cidr:
            orig_ip_cidr = current_ip_cidr

        path = IP_CIDR_PATH.format(tenant=tenant_name,
                                   segment=segment_name,
                                   ip_cidr=orig_ip_cidr)
        self.rest_call(path, json.dumps({"ip-cidr": current_ip_cidr}),
                       verb='PUT')

        return True

    def _get_segment_interface(self, tenant_name):
        path = SEGMENT_IFS_PATH.format(tenant=tenant_name)
        code, result = self.rest_call(path, json.dumps({}), verb='GET')
        return json.loads(result)

    def delete_net(self, tenant_name, segment_name):
        if not (tenant_name and segment_name):
            emsg = "Invalid parameter for delete_net: "\
                   "tenant_name=%(tenant_name)s, "\
                   "segment_name=%(segment_name)s" % {
                       'tenant_name': tenant_name,
                       'segment_name': segment_name}
            LOG.debug(emsg)
            raise exceptions.InvalidInput(error_message=emsg)

        self._renew_session()

        # delete segment interface
        path = SEGMENT_IF_PATH.format(tenant=tenant_name, segment=segment_name)
        self.rest_call(path, json.dumps({}), verb='DELETE')

        # check if other nets remain
        interfaces = self._get_segment_interface(tenant_name)
        if len(interfaces) > 0:
            LOG.debug("skip to delete a static route and tenant interfaces"
                      " in tenant(%(tenant_name)s)",
                      {'tenant_name': tenant_name})
            return True

        # delete static route
        path = STATIC_ROUTE_PATH.format(tenant=tenant_name)
        self.rest_call(path, json.dumps({}), verb='DELETE')

        # delete tenant-interface
        path = TENANT_IF_PATH.format(tenant='system',
                                     remote=tenant_name)
        self.rest_call(path, json.dumps({}), verb='DELETE')

        path = TENANT_IF_PATH.format(tenant=tenant_name,
                                     remote='system')
        self.rest_call(path, json.dumps({}), verb='DELETE')

        return True

    def delete_subnet(self, tenant_name, segment_name, ip_cidr):
        if not (tenant_name and segment_name and ip_cidr):
            emsg = "Invalid parameter for delete_subnet: "\
                   "tenant_name=%(tenant_name)s, "\
                   "segment_name=%(segment_name)s, "\
                   "ip_cidr=%(ip_cidr)s" % {
                       'tenant_name': tenant_name,
                       'segment_name': segment_name,
                       'ip_cidr': ip_cidr}
            LOG.debug(emsg)
            raise exceptions.InvalidInput(error_message=emsg)

        self._renew_session()

        # delete segment interface
        path = IP_CIDR_PATH.format(tenant=tenant_name,
                                   segment=segment_name,
                                   ip_cidr=ip_cidr)
        self.rest_call(path, json.dumps({}), verb='DELETE')

        return True
