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

from neutron.common import exceptions


class BCFRestError(exceptions.NeutronException):
    message = "Fail to call BCF REST API: code=%(code)s, result=%(result)s, "\
              "method=%(method)s, url=%(url)s, data=%(data)s"

    def __init__(self, **kwargs):
        self.code = kwargs.get('code')
        self.result = kwargs.get('result')
        self.method = kwargs.get('method')
        self.url = kwargs.get('url')
        self.data = kwargs.get('data')
        super(BCFRestError, self).__init__(**kwargs)


class UpdateNetworkNameError(exceptions.NeutronException):
    message = "Updating network name is not allowed."
