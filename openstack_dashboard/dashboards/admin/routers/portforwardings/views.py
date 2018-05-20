# Copyright (c) 2013-2015 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from django.utils.translation import ugettext_lazy as _

from openstack_dashboard.dashboards.admin.routers.portforwardings \
    import forms as admin_forms
from openstack_dashboard.dashboards.project.routers.portforwardings \
    import views as project_views


class AddPortForwardingRuleView(project_views.AddPortForwardingRuleView):
    form_class = admin_forms.AddPortForwardingRule
    template_name = 'admin/routers/portforwardings/create.html'
    success_url = 'horizon:admin:routers:detail'
    failure_url = 'horizon:admin:routers:detail'
    page_title = _("Add Port Forwarding Rule")


class UpdatePortForwardingRuleView(project_views.UpdatePortForwardingRuleView):
    form_class = admin_forms.UpdatePortForwardingRule
    template_name = 'admin/routers/portforwardings/update.html'
    success_url = 'horizon:admin:routers:detail'
    failure_url = 'horizon:admin:routers:detail'
    page_title = _("Update Port Forwarding Rule")
