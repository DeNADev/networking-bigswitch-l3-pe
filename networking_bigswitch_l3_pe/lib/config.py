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

from oslo_config import cfg

bcf_pe_opts = [
    cfg.StrOpt('api_url', default='https://localhost:8443/api/v1',
               help="A BCF REST API. This should be a fully qualified url "
                    "of the form (i.e. https://controller:8443/api/v1)"),
]


def register_config():
    cfg.CONF.register_opts(bcf_pe_opts, "networking_bigswitch_l3_pe")
