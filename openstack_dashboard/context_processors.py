# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
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
"""
Context processors used by Horizon.
"""

import ast
from collections import namedtuple
import logging
import re
from time import time

from django.conf import settings
from horizon import conf
from openstack_dashboard import api
from openstack_dashboard.contrib.developer.profiler import api as profiler

system_name_cache = ''
cache_update_time = 0

LOG = logging.getLogger(__name__)


def openstack(request):
    """Context processor necessary for OpenStack Dashboard functionality.

    The following variables are added to the request context:

    ``authorized_tenants``
        A list of tenant objects which the current user has access to.

    ``regions``

        A dictionary containing information about region support, the current
        region, and available regions.
    """
    global system_name_cache
    global cache_update_time
    context = {}

    # Auth/Keystone context
    context.setdefault('authorized_tenants', [])
    if request.user.is_authenticated():
        # WRS: Attempt to retrieve the authorized tenants from
        # the cookie if it has been cached
        tenant_cookie = request.COOKIES.get("authorized_tenants", None)
        if tenant_cookie:
            LOG.debug("Retrieved 'authorized_tenants' from COOKIE: %s",
                      tenant_cookie)
            tenant_list = ast.literal_eval(tenant_cookie)
            tenants = []
            for tenant in tenant_list:
                tenant = namedtuple('projects',
                                    tenant.keys())(*tenant.values())
                tenants.append(tenant)
        else:
            tenants = request.user.authorized_tenants
            LOG.debug("Retrieved authorized tenants from Keystone: %s",
                      tenants)

        context['authorized_tenants'] = [
            t for t in tenants if t.enabled]

    # Region context/support
    available_regions = getattr(settings, 'AVAILABLE_REGIONS', [])
    available_regions = [a for a in available_regions if a not in
                         getattr(settings, 'REGION_EXCLUSIONS', [])]
    regions = {'support': len(available_regions) > 1,
               'current': {'endpoint': request.session.get('region_endpoint'),
                           'name': request.session.get('region_name')},
               'available': [{'endpoint': region[0], 'name':region[1]} for
                             region in available_regions]}

    # K2K Federation Service Providers context/support
    available_providers = request.session.get('keystone_providers', [])
    if available_providers:
        provider_id = request.session.get('keystone_provider_id', None)
        provider_name = None
        for provider in available_providers:
            if provider['id'] == provider_id:
                provider_name = provider.get('name')

        keystone_providers = {
            'support': len(available_providers) > 1,
            'current': {
                'name': provider_name,
                'id': provider_id
            },
            'available': [
                {'name': keystone_provider['name'],
                 'id': keystone_provider['id']}
                for keystone_provider in available_providers]
        }
    else:
        keystone_providers = {'support': False}

    context['keystone_providers'] = keystone_providers
    context['regions'] = regions

    # Adding webroot access
    context['WEBROOT'] = getattr(settings, "WEBROOT", "/")

    # Adding profiler support flag
    profiler_settings = getattr(settings, 'OPENSTACK_PROFILER', {})
    profiler_enabled = profiler_settings.get('enabled', False)
    context['profiler_enabled'] = profiler_enabled
    if profiler_enabled and 'profile_page' in request.COOKIES:
        index_view_id = request.META.get(profiler.ROOT_HEADER, '')
        hmac_keys = profiler_settings.get('keys', [])
        context['x_trace_info'] = profiler.update_trace_headers(
            hmac_keys, parent_id=index_view_id)

    context['JS_CATALOG'] = get_js_catalog(conf)

    if (request.user.is_authenticated() and request.user.is_superuser and
            api.base.is_service_enabled(request, 'platform')):

        cur_time = long(time())
        delta_time = cur_time - cache_update_time
        if delta_time >= 60:
            # Get system name
            try:
                systems = api.sysinv.system_list(request)
                system_name_cache = systems[0].name
                cache_update_time = cur_time
            except Exception:
                system_name_cache = ''
        context['system_name'] = system_name_cache
        context['alarmbanner'] = True
    else:
        context['system_name'] = ''
        context['alarmbanner'] = False

    return context


def get_js_catalog(conf):
    # Search for external plugins and append to javascript message catalog
    # internal plugins are under the openstack_dashboard domain
    # so we exclude them from the js_catalog
    js_catalog = ['horizon', 'openstack_dashboard']
    regex = re.compile(r'^openstack_dashboard')
    all_plugins = conf.HORIZON_CONFIG.get('plugins', [])
    js_catalog.extend(p for p in all_plugins if not regex.search(p))
    return '+'.join(js_catalog)
