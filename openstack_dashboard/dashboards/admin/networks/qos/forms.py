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
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#


import logging

from django.core.urlresolvers import reverse  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import exceptions
from horizon import forms
from horizon import messages
from openstack_dashboard import api

LOG = logging.getLogger(__name__)


class QoSPolicyForm(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255,
                           label=_("Name"),
                           required=True)
    description = forms.CharField(max_length=255,
                                  label=_("Description"),
                                  required=False)
    weight = forms.IntegerField(label=_("Scheduler Weight"),
                                min_value=1,
                                required=True)

    def _get_params(self, request, data):
        params = {'name': data['name'],
                  'description': data['description'],
                  'policies': {
                      api.neutron.QOS_TYPE_SCHEDULER: {
                          'weight': data['weight']}}}
        return params


class CreateQoSPolicy(QoSPolicyForm):
    tenant_id = forms.ChoiceField(label=_("Project"),
                                  required=False)

    @classmethod
    def _instantiate(cls, request, *args, **kwargs):
        return cls(request, *args, **kwargs)

    def __init__(self, request, *args, **kwargs):
        super(CreateQoSPolicy, self).__init__(request, *args, **kwargs)

        tenant_choices = [('', _("Select a project"))]
        tenants, has_more = api.keystone.tenant_list(request)
        for tenant in tenants:
            if tenant.enabled:
                tenant_choices.append((tenant.id, tenant.name))
        self.fields['tenant_id'].choices = tenant_choices

    def handle(self, request, data):
        try:
            params = self._get_params(request, data)
            params['tenant_id'] = data['tenant_id']
            qos = api.neutron.qos_create(request, **params)
            msg = (_('QoS policy %s was successfully created.') %
                   data['description'])
            LOG.debug(msg)
            messages.success(request, msg)
            return qos
        except Exception:
            redirect = reverse('horizon:admin:networks:index')
            msg = _('Failed to create QoS policy %s') % data['name']
            exceptions.handle(request, msg, redirect=redirect)


class UpdateQosPolicy(QoSPolicyForm):
    id = forms.CharField(widget=forms.HiddenInput)

    failure_url = 'horizon:admin:networks:index'

    def handle(self, request, data):
        try:
            params = self._get_params(request, data)
            msg = (_('QoS policy %s was successfully updated.') %
                   data['description'])
            qos = api.neutron.qos_update(
                request, data['id'], **params)
            LOG.debug(msg)
            messages.success(request, msg)
            return qos
        except Exception:
            msg = _('Failed to update QoS policy %s') % data['name']
            LOG.info(msg)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
