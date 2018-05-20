# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Nebula, Inc.
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
#
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#


import logging

from collections import OrderedDict as SortedDict
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import exceptions
from horizon import messages
from horizon import tabs
from openstack_dashboard.api import base
from openstack_dashboard.api import keystone
from openstack_dashboard.api import neutron
from openstack_dashboard.dashboards.admin.networks import \
    tables as networks_tables
from openstack_dashboard.dashboards.project.networks import \
    wrs_tabs as networks_tabs

LOG = logging.getLogger(__name__)


class NetworkingTable(tabs.TableTab):
    def _get_tenant_list(self):
        if not hasattr(self, "_tenants"):
            try:
                tenants, has_more = keystone.tenant_list(self.request)
            except Exception:
                tenants = []
                msg = _('Unable to retrieve instance project information.')
                exceptions.handle(self.request, msg)
            tenant_dict = SortedDict([(t.id, t) for t in tenants])
            self._tenants = tenant_dict
        return self._tenants


class TenantNetworkTab(NetworkingTable, networks_tabs.NetworkTab):
    table_classes = (networks_tables.NetworksTable,)
    name = _("Networks")
    slug = "networks"
    template_name = ("horizon/common/_detail_table.html")

    def _get_agents_data(self, network):
        agents = []
        data = _("Unknown")
        try:
            if neutron.is_extension_supported(self.request,
                                              'dhcp_agent_scheduler'):
                # This method is called for each network. If agent-list cannot
                # be retrieved, we will see many pop-ups. So the error message
                # will be popup-ed in get_data() below.
                agents = neutron.list_dhcp_agent_hosting_networks(
                    self.request, network)
                data = len(agents)
        except Exception:
            self.exception = True
        return data

    def _get_search_opts(self):
        filters = self.get_filters()
        if filters and filters.get('project'):
            project = filters.pop('project')
            if project:
                tenant_dict = self._get_tenant_list()
                for id, tenant in tenant_dict.items():
                    if project == getattr(tenant, 'name', None):
                        project = id
                        break
                filters['tenant_id'] = project
        for name, mapping in self.FILTERS_MAPPING.items():
            if name in filters and filters[name] not in mapping.values():
                msg = _('Invalid filter string, filtering not applied.')
                messages.warning(self.request, msg)
                filters = {}
        return filters

    def get_networks_data(self):
        try:
            opts = self._get_search_opts()
            networks = neutron.network_list(self.tab_group.request, **opts)
        except Exception:
            networks = []
            msg = _('Unable to get tenant network list.')
            exceptions.check_message(["Connection", "refused"], msg)
            raise
        if networks:
            self.exception = False
            tenant_dict = self._get_tenant_list()
            for n in networks:
                # Set tenant name
                tenant = tenant_dict.get(n.tenant_id, None)
                n.tenant_name = getattr(tenant, 'name', None)
                # If name is empty use UUID as name
                n.set_id_as_name_if_empty()
                # Get number of DHCP agents
                n.num_agents = self._get_agents_data(n.id)

            if self.exception:
                msg = _('Unable to list dhcp agents hosting network.')
                exceptions.handle(self.request, msg)

        return networks


class NetworkTabs(tabs.TabGroup):
    slug = "networks"
    tabs = (TenantNetworkTab, )
    sticky = True
