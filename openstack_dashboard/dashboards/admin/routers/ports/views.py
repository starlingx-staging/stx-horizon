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

from horizon import tabs

from openstack_dashboard.dashboards.admin.routers.ports \
    import forms as admin_forms
from openstack_dashboard.dashboards.admin.routers.ports \
    import tabs as project_tabs
from openstack_dashboard.dashboards.project.routers.ports \
    import views as project_views


class SetGatewayView(project_views.SetGatewayView):
    form_class = admin_forms.SetGatewayForm
    template_name = 'admin/routers/ports/setgateway.html'
    success_url = 'horizon:admin:routers:index'
    failure_url = 'horizon:admin:routers:index'


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.PortDetailTabs
    template_name = 'admin/networks/ports/detail.html'
