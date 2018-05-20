# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#


import logging

from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon import tabs
from openstack_dashboard.api import base
from openstack_dashboard.api import neutron
from openstack_dashboard.dashboards.project.networks import \
    tables as networks_tables

LOG = logging.getLogger(__name__)


class NetworkTab(tabs.TableTab, tables.DataTableView):
    FILTERS_MAPPING = {'shared': {_("yes"): True, _("no"): False},
                       'router:external': {_("yes"): True, _("no"): False},
                       'admin_state_up': {_("up"): True, _("down"): False}}

    def get_filters(self, filters=None):
        self.table = self._tables['networks']
        self.handle_server_filter(self.request, table=self.table)
        self.update_server_filter_action(self.request, table=self.table)
        filters = super(NetworkTab, self).get_filters(filters,
                                                      self.FILTERS_MAPPING)
        return filters


class TenantNetworkTab(NetworkTab):
    table_classes = (networks_tables.NetworksTable,)
    name = _("Networks")
    slug = "networks"
    template_name = ("horizon/common/_detail_table.html")

    def get_networks_data(self):
        try:
            search_opts = self.get_filters()
            for name, mapping in self.FILTERS_MAPPING.items():
                if name in search_opts and \
                        search_opts[name] not in mapping.values():
                    msg = _('Invalid filter string, filtering not applied.')
                    messages.warning(self.request, msg)
                    search_opts = {}

            tenant_id = self.request.user.tenant_id
            networks = neutron.network_list_for_tenant(
                self.request, tenant_id, include_external=True, **search_opts)
        except Exception:
            msg = _('Unable to get network list.')
            exceptions.check_message(["Connection", "refused"], msg)
            raise
        return networks


class NetworkTabs(tabs.TabGroup):
    slug = "networks"
    tabs = (TenantNetworkTab, )
    sticky = True
