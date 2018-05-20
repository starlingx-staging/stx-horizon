# Copyright (c) 2013-2015 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from openstack_dashboard.dashboards.project.routers.portforwardings \
    import tables as project_tables


LOG = logging.getLogger(__name__)


class AddPortForwardingRule(project_tables.AddPortForwardingRule):
    url = "horizon:admin:routers:addportforwardingrule"


class UpdatePortForwardingRule(project_tables.UpdatePortForwardingRule):
    url = "horizon:admin:routers:updateportforwardingrule"


class RemovePortForwardingRule(project_tables.RemovePortForwardingRule):
    failure_url = 'horizon:admin:routers:detail'


def _get_port_link_url(rule):
    port = rule['port']
    link = 'horizon:admin:networks:ports:detail'
    return reverse(link, args=(port.id,))


class PortForwardingRulesTable(project_tables.PortForwardingRulesTable):

    port = tables.Column(project_tables._get_port_name_or_id,
                         verbose_name=_("Port"),
                         link=_get_port_link_url)

    class Meta(object):
        name = "portforwardings"
        verbose_name = _("Port Forwarding Rules")
        table_actions = (AddPortForwardingRule, RemovePortForwardingRule)
        row_actions = (UpdatePortForwardingRule, RemovePortForwardingRule, )
