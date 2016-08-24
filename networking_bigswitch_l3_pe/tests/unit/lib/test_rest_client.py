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

from mock import Mock
from mock import patch
from neutron.tests import base
import networking_bigswitch_l3_pe.lib.config
from networking_bigswitch_l3_pe.lib.rest_client import BCFRestError
from networking_bigswitch_l3_pe.lib.rest_client import RestClient


class RestClientTestCase(base.BaseTestCase):

    def setUp(self):
        super(RestClientTestCase, self).setUp()
        networking_bigswitch_l3_pe.lib.config.register_config()

    def _setup_mock(self, code, responses):
        ret = Mock()
        ret.code = code
        ret.read.side_effect = ['{"session_cookie": "dummy"}'] + responses
        return ret

    def _setup_rest_client(self):
        return RestClient('http://127.0.0.1/', 'admin', 'password')

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_get_segment_interface(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200, ['[]'])
        client = self._setup_rest_client()

        client._renew_session()
        ret = client._get_segment_interface('tenant_test')
        self.assertEqual([], ret)

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_create_net(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200,
                                                     ['[]', '[]', '[]', '[]'])
        client = self._setup_rest_client()

        ret = client.create_net('tenant_test', 'net_test')
        self.assertTrue(ret)

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_create_net_with_wrong_code(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200, [])
        client = self._setup_rest_client()

        mock_urlopen.return_value.code = 400
        mock_urlopen.return_value.read.side_effect = ['[]']
        self.assertRaises(BCFRestError,
                          client.create_net, 'tenant_test', 'net_test')

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_create_subnet(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200, ['[]'])
        client = self._setup_rest_client()

        ret = client.create_subnet('tenant_test',
                                   'net_test', '192.168.0.254/24')
        self.assertTrue(ret)

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_delete_subnet(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200, ['[]'])
        client = self._setup_rest_client()

        ret = client.delete_subnet('tenant_test',
                                   'net_test', '192.168.0.254/24')
        self.assertTrue(ret)

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_delete_net(self, mock_urlopen):
        mock_urlopen.return_value =\
            self._setup_mock(200, ['[]', '[]', '[]', '[]', '[]'])
        client = self._setup_rest_client()

        ret = client.delete_net('tenant_test', 'net_test')
        self.assertTrue(ret)

    @patch('networking_bigswitch_l3_pe.lib.rest_client.urllib2.urlopen')
    def test_delete_net_when_other_net_remain(self, mock_urlopen):
        mock_urlopen.return_value = self._setup_mock(200, ['[]', '[{}]'])
        client = self._setup_rest_client()

        ret = client.delete_net('tenant_test', 'net_test')
        self.assertTrue(ret)
