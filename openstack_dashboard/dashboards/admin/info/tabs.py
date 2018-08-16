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
# Copyright (c) 2013-2015 Wind River Systems, Inc.
#

import logging

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs
from openstack_dashboard.api import base
from openstack_dashboard.api import cinder
from openstack_dashboard.api import heat
from openstack_dashboard.api import iservice
from openstack_dashboard.api import neutron
from openstack_dashboard.api import nova
from openstack_dashboard.dashboards.admin.info import constants
from openstack_dashboard.dashboards.admin.info import tables
from openstack_dashboard.utils import objectify

LOG = logging.getLogger(__name__)


class ServicesTab(tabs.TableTab):
    table_classes = (tables.ServicesTable,)
    name = tables.ServicesTable.Meta.verbose_name
    slug = tables.ServicesTable.Meta.name
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME

    def generate_catalog_endpoints(self, catalog):
        for service in catalog:
            regions = set(endpoint['region'] for endpoint
                          in service['endpoints'])
            for region in regions:
                endpoints = [endpoint for endpoint
                             in service['endpoints']
                             if endpoint['region'] == region]
                # sort the endpoints, so they appear in consistent order
                endpoints.sort(key=lambda endpoint: endpoint.get('interface'))
                yield {'id': service['name'] + region,
                       'name': service['name'],
                       'type': service['type'],
                       'region': region,
                       'endpoints': endpoints,
                       }

    def get_services_data(self):
        request = self.tab_group.request
        catalog = request.user.service_catalog
        services = list(self.generate_catalog_endpoints(catalog))
        return services


class NovaServicesTab(tabs.TableTab):
    table_classes = (tables.NovaServicesTable,)
    name = tables.NovaServicesTable.Meta.verbose_name
    slug = tables.NovaServicesTable.Meta.name
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME
    permissions = ('openstack.services.compute',)

    def get_nova_services_data(self):
        try:
            services = nova.service_list(self.tab_group.request)
        except Exception:
            msg = _('Unable to get nova services list.')
            exceptions.check_message(["Connection", "refused"], msg)
            exceptions.handle(self.request, msg)
            services = []
        return services


class CinderServicesTab(tabs.TableTab):
    table_classes = (tables.CinderServicesTable,)
    name = tables.CinderServicesTable.Meta.verbose_name
    slug = tables.CinderServicesTable.Meta.name
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME
    permissions = (
        ('openstack.services.volume', 'openstack.services.volumev2'),
    )

    def get_cinder_services_data(self):
        try:
            services = cinder.service_list(self.tab_group.request)
        except Exception:
            msg = _('Unable to get cinder services list.')
            exceptions.check_message(["Connection", "refused"], msg)
            exceptions.handle(self.request, msg)
            services = []
        return services


class ControllerServicesTab(tabs.TableTab):
    table_classes = (tables.ControllerServicesTable,)
    name = _("Controller Services")
    slug = "controller_services"
    template_name = ("horizon/common/_detail_table.html")

    def _find_service_group_names(self, sdas):
        service_group_names_set = set()
        for sda in sdas:
            service_group_names_set.add(sda.service_group_name)

        service_group_names_list = list(service_group_names_set)

        return service_group_names_list

    def _update_service_group_states_ORIG(self, service_group_name,
                                          sdas, nodes):
        entry = {}

        for sda in sdas:
            admin = ""
            for n in nodes:
                if n.name == sda.node_name:
                    if n.administrative_state.lower() == "locked":
                        admin = "-locked"
                    else:
                        admin = "-unlocked-" + n.operational_state.lower()

            if sda.service_group_name == service_group_name:
                if sda.state == "active":
                    entry.update({'active_activity': 'active'})
                    entry.update({'active_hostname': sda.node_name})
                    entry.update({'active_state': sda.state})  # enabled?
                else:
                    entry.update({'standby_activity': sda.state})
                    entry.update({'standby_hostname': sda.node_name})
                    entry.update({'standby_state': admin + sda.state})

        return entry

    def _update_service_group_states(self, service_group_name, sdas, nodes):
        entry = {}

        for sda in sdas:
            # admin = ""
            for n in nodes:
                if n.name == sda.node_name:
                    if n.administrative_state.lower() == "locked":
                        dstate = "locked"
                    elif n.operational_state.lower() == "enabled":
                        dstate = "standby"
                    else:
                        dstate = n.operational_state.lower()

            if sda.service_group_name == service_group_name:
                state_str = sda.state
                if sda.status != "":
                    state_str += '-' + sda.status
                    if sda.condition != "":
                        state_str += ' [' + sda.condition + ']'

                if sda.state == "active":
                    if sda.node_name == "controller-0":
                        entry.update({'c0_activity': 'active'})
                        entry.update({'c0_hostname': sda.node_name})
                        entry.update({'c0_state': state_str})
                    elif sda.node_name == "controller-1":
                        entry.update({'c1_activity': 'active'})
                        entry.update({'c1_hostname': sda.node_name})
                        entry.update({'c1_state': state_str})
                else:
                    if dstate == "standby":
                        dstate = state_str

                    if sda.node_name == "controller-0":
                        entry.update({'c0_activity': sda.state})
                        entry.update({'c0_hostname': sda.node_name})
                        entry.update({'c0_state': dstate})
                    elif sda.node_name == "controller-1":
                        entry.update({'c1_activity': sda.state})
                        entry.update({'c1_hostname': sda.node_name})
                        entry.update({'c1_state': dstate})

        return entry

    def get_controller_services_data(self):
        try:
            # instances before servicegroups because for it updates sg db
            # instances = iservice.iservice_list(self.tab_group.request)
            # servicegroups = iservice.iservicegroup_list(
            #                                       self.tab_group.request)
            nodes = iservice.sm_nodes_list(self.tab_group.request)
            # fields = ['id', 'name', 'state', 'online']

            sdas = iservice.sm_sda_list(self.tab_group.request)
            # controller-1 is not in sda when installing, but is in node-list
            #     with state "unknown"
            # fields = ['uuid', 'service_group_name', 'node_name',
            #           'state', 'status', 'condition']

            services = []

            sgs = self._find_service_group_names(sdas)

            sdaid = 0
            for sg in sgs:
                sdaid += 1
                entry = {}
                entry.update({'id': sdaid})
                entry.update({'servicename': sg})
                sg_states = self._update_service_group_states(sg, sdas, nodes)
                entry.update(sg_states)

                # Need to latch if any sg is enabled
                if 'c0_activity' in entry.keys():
                    sgstate = entry['c0_activity']
                    if sgstate == "active":
                        entry.update({'sgstate': sgstate})
                elif 'c1_activity' in entry.keys():
                    sgstate = entry['c1_activity']
                    if sgstate == "active":
                        entry.update({'sgstate': sgstate})

                if sgstate != "active":
                    entry.update({'sgstate': sgstate})

                if entry != {}:
                    entry_object = objectify.objectify(entry)
                    services.append(entry_object)

            # services_object = objectify.objectify(services)

        except Exception:
            services = []
            msg = _('Unable to get controller services list.')
            exceptions.check_message(["Connection", "refused"], msg)
            raise

        return services

    def allowed(self, request):
        return base.is_stx_region(request)


class NetworkAgentsTab(tabs.TableTab):
    table_classes = (tables.NetworkAgentsTable,)
    name = tables.NetworkAgentsTable.Meta.verbose_name
    slug = tables.NetworkAgentsTable.Meta.name
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME

    def allowed(self, request):
        try:
            return (base.is_service_enabled(request, 'network') and
                    neutron.is_extension_supported(request, 'agent'))
        except Exception:
            exceptions.handle(request, _('Unable to get network agents info.'))
            return False

    def get_network_agents_data(self):
        try:
            agents = neutron.agent_list(self.tab_group.request)
        except Exception:
            msg = _('Unable to get network agents list.')
            exceptions.check_message(["Connection", "refused"], msg)
            exceptions.handle(self.request, msg)
            agents = []
        return agents


class HeatServiceTab(tabs.TableTab):
    table_classes = (tables.HeatServiceTable,)
    name = tables.HeatServiceTable.Meta.verbose_name
    slug = tables.HeatServiceTable.Meta.name
    template_name = constants.INFO_DETAIL_TEMPLATE_NAME

    def allowed(self, request):
        try:
            return base.is_service_enabled(request, 'orchestration')
        except Exception:
            exceptions.handle(request, _('Orchestration service is disabled.'))
            return False

    def get_heat_services_data(self):
        try:
            services = heat.service_list(self.tab_group.request)
        except Exception:
            msg = _('Unable to get Orchestration service list.')
            exceptions.check_message(["Connection", "refused"], msg)
            exceptions.handle(self.request, msg)
            services = []
        return services


class SystemInfoTabs(tabs.TabGroup):
    slug = "system_info"
    tabs = (ServicesTab, ControllerServicesTab, NovaServicesTab,
            CinderServicesTab,
            NetworkAgentsTab, HeatServiceTab)
    sticky = True
