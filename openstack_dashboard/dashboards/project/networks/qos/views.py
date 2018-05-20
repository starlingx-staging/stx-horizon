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


from django.core.urlresolvers import reverse_lazy  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import exceptions
from horizon import tables
from openstack_dashboard import api
from openstack_dashboard.dashboards.project.networks.qos import \
    tables as qos_tables


class DetailView(tables.DataTableView):
    table_class = qos_tables.QoSPolicyTable
    template_name = 'project/networks/qos/detail.html'
    failure_url = reverse_lazy('horizon:project:networks:index')
    page_title = '{{ "QoS Policy Detail: "|add:qos.name }}'

    def get_data(self):
        try:
            qos_id = self.kwargs['qos_id']
            self.table.kwargs['qos'] = self._get_data()
            qos = api.neutron.qos_get(self.request, qos_id)
        except Exception:
            qos = []
            msg = _('QoS policy can not be retrieved.')
            exceptions.handle(self.request, msg)
        return qos

    def _get_data(self):
        if not hasattr(self, "_qos"):
            try:
                qos_id = self.kwargs['qos_id']
                qos = api.neutron.qos_get(self.request, qos_id)
            except Exception:
                redirect = self.failure_url
                exceptions.handle(self.request,
                                  _('Unable to retrieve details for '
                                    'QoS policy "%s".') % qos_id,
                                  redirect=redirect)
            self._qos = qos
        return self._qos

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["qos"] = self._get_data()
        return context
