# Copyright (c) 2013-2015 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging

from openstack_dashboard.dashboards.project.routers.portforwardings \
    import forms as project_forms


LOG = logging.getLogger(__name__)


class AddPortForwardingRule(project_forms.AddPortForwardingRule):

    failure_url = 'horizon:admin:routers:detail'


class UpdatePortForwardingRule(project_forms.UpdatePortForwardingRule):

    failure_url = 'horizon:admin:routers:detail'
