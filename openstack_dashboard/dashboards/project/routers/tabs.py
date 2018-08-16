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
#
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#


from django.utils.translation import ugettext_lazy as _

from horizon import tabs

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.routers.extensions.extraroutes\
    import tabs as er_tabs
from openstack_dashboard.dashboards.project.routers.portforwardings\
    import tables as pftbl
from openstack_dashboard.dashboards.project.routers.ports import tables as ptbl


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = "project/routers/_detail_overview.html"

    def get_context_data(self, request):
        return {"router": self.tab_group.kwargs['router'],
                'ha_supported': api.neutron.
                get_feature_permission(self.request, "l3-ha", "get")
                }


class InterfacesTab(tabs.TableTab):
    table_classes = (ptbl.PortsTable,)
    name = _("Interfaces")
    slug = "interfaces"
    template_name = "horizon/common/_detail_table.html"

    def get_interfaces_data(self):
        return self.tab_group.kwargs['ports']


class PortForwardingTab(tabs.TableTab):
    table_classes = (pftbl.PortForwardingRulesTable,)
    name = _("Port Forwarding")
    slug = "portforwardings"
    template_name = "horizon/common/_detail_table.html"

    def get_portforwardings_data(self):
        return self.tab_group.kwargs['portforwardings']

    def allowed(self, request):
        return api.base.is_stx_region(request)


class RouterDetailTabs(tabs.DetailTabsGroup):
    slug = "router_details"
    tabs = (OverviewTab, InterfacesTab, PortForwardingTab,
            er_tabs.ExtraRoutesTab)
    sticky = True
