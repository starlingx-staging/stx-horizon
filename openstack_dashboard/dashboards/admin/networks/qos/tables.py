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
from django import template
from django.utils.translation import ugettext_lazy as _  # noqa
from django.utils.translation import ungettext_lazy  # noqa
from neutronclient.common import exceptions as neutron_exceptions


from horizon import exceptions
from horizon import tables
from openstack_dashboard import api

LOG = logging.getLogger(__name__)


def get_policies(qos):
    template_name = 'project/networks/qos/_policies.html'
    context = {"qos": qos}
    return template.loader.render_to_string(template_name, context)


class DeleteQoSPolicy(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete QoS Policy",
            u"Delete QoS Policies",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Delete QoS Policy",
            u"Delete QoS Policies",
            count
        )

    def delete(self, request, obj_id):
        try:
            api.neutron.qos_delete(request, obj_id)
        except neutron_exceptions.NeutronClientException as e:
            LOG.info(e.message)
            redirect = reverse('horizon:admin:networks:index')
            exceptions.handle(request, e.message, redirect=redirect)
        except Exception:
            msg = _('Failed to delete QoS policy %s') % obj_id
            LOG.info(msg)
            redirect = reverse('horizon:admin:networks:index')
            exceptions.handle(request, msg, redirect=redirect)


class CreateQoSPolicy(tables.LinkAction):
    name = "create"
    verbose_name = _("Create QoS Policy")
    url = "horizon:admin:networks:qos:create"
    classes = ("ajax-modal", "btn-create")


class EditQoSPolicy(tables.LinkAction):
    name = "update"
    verbose_name = _("Edit QoS Policy")
    url = "horizon:admin:networks:qos:update"
    classes = ("ajax-modal", "btn-edit")


class QosFilterAction(tables.FilterAction):
    def filter(self, table, qoses, filter_string):
        """Naive case-insensitive search."""
        q = filter_string.lower()
        return [qos for qos in qoses
                if q in qos.name.lower()]


class QoSPolicyTable(tables.DataTable):
    tenant = tables.Column("tenant_name", verbose_name=_("Project"))
    name = tables.Column("name", verbose_name=_("Name"),
                         link='horizon:admin:networks:qos:detail')
    policy = tables.Column(get_policies,
                           verbose_name=_("Policy"))

    class Meta(object):
        name = "qos"
        verbose_name = _("QoS Policies")
        table_actions = (CreateQoSPolicy, DeleteQoSPolicy, QosFilterAction)
        row_actions = (EditQoSPolicy, DeleteQoSPolicy)
