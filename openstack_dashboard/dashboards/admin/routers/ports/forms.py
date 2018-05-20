# Copyright 2012,  Nachi Ueno,  NTT MCL,  Inc.
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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import messages
from openstack_dashboard import api

from openstack_dashboard.dashboards.project.routers.ports \
    import forms as project_forms

LOG = logging.getLogger(__name__)


class SetGatewayForm(project_forms.SetGatewayForm):
    network_id = forms.ChoiceField(label=_("External Network"))
    ip_address = forms.IPField(
        label=_("IP Address (optional)"),
        required=False,
        initial="",
        help_text=_("IP address of gateway interface (e.g. 192.168.0.254). "
                    "Specify an explicit address to use when creating the "
                    "gateway interface.  If one is not specified an address "
                    "will be allocated from the external subnet."),
        version=forms.IPv4 | forms.IPv6,
        mask=False)
    router_name = forms.CharField(label=_("Router Name"),
                                  widget=forms.TextInput(
                                      attrs={'readonly': 'readonly'}))
    router_id = forms.CharField(label=_("Router ID"),
                                widget=forms.TextInput(
                                    attrs={'readonly': 'readonly'}))
    enable_snat = forms.BooleanField(label=_("Enable SNAT"),
                                     initial=True, required=False)

    failure_url = 'horizon:admin:routers:index'

    def handle(self, request, data):
        try:
            ip_address = data.get('ip_address') or None
            enable_snat = data.get('enable_snat', True)
            api.neutron.router_add_gateway(request,
                                           data['router_id'],
                                           data['network_id'],
                                           ip_address=ip_address,
                                           enable_snat=enable_snat)
            msg = _('Gateway interface is added')
            LOG.debug(msg)
            messages.success(request, msg)
            return True
        except Exception as e:
            msg = _('Failed to set gateway %s') % e
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
