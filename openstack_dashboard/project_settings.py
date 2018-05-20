#
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging

from openstack_dashboard.api import neutron


LOG = logging.getLogger(__name__)

NEUTRON_SETTING_FIELDS = ("mac_filtering",)

SETTING_FIELDS = NEUTRON_SETTING_FIELDS


def get_default_setting_data(request, tenant_id=None):
    """Retrieve default settings."""
    tenant_id = tenant_id or request.user.tenant_id
    # Neutron does not provide a default get method so return the settings
    # for the current project.
    neutron_settings = neutron.tenant_setting_get(request, tenant_id)
    return neutron_settings


def get_tenant_setting_data(request, tenant_id=None):
    """Retrieve current settings for the given tenant id."""
    tenant_id = tenant_id or request.user.tenant_id
    neutron_settings = neutron.tenant_setting_get(request, tenant_id)
    return neutron_settings
