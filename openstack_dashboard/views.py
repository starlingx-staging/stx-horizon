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

from django.conf import settings
from django.core import urlresolvers
from django import shortcuts
import django.views.decorators.vary
from six.moves import urllib

import horizon
from horizon import base
from horizon import exceptions
from horizon import notifications


MESSAGES_PATH = getattr(settings, 'MESSAGES_PATH', None)


def get_user_home(user):
    dashboard = horizon.get_default_dashboard()
    dc_mode = getattr(settings, 'DC_MODE', False)

    if user.is_superuser:
        if getattr(user, 'services_region', None) == 'SystemController':
            try:
                dashboard = horizon.get_dashboard('dc_admin')
            except base.NotRegistered:
                pass

    if getattr(user, 'services_region', None) == 'RegionOne' and dc_mode:
        try:
            if user.is_superuser:
                dashboard = horizon.get_dashboard('admin').\
                    get_panel("inventory")
            else:
                dashboard = horizon.get_dashboard('project').\
                    get_panel("api_access")
        except base.NotRegistered:
            pass

    return dashboard.get_absolute_url()


@django.views.decorators.vary.vary_on_cookie
def splash(request):
    if not request.user.is_authenticated():
        raise exceptions.NotAuthenticated()

    response = shortcuts.redirect(horizon.get_user_home(request.user))
    if 'logout_reason' in request.COOKIES:
        response.delete_cookie('logout_reason')
    if 'logout_status' in request.COOKIES:
        response.delete_cookie('logout_status')
    # Display Message of the Day message from the message files
    # located in MESSAGES_PATH
    if MESSAGES_PATH:
        notifications.process_message_notification(request, MESSAGES_PATH)
    return response


def get_url_with_pagination(request, marker_name, prev_marker_name, url_string,
                            object_id=None):
    if object_id:
        url = urlresolvers.reverse(url_string, args=(object_id,))
    else:
        url = urlresolvers.reverse(url_string)
    marker = request.GET.get(marker_name, None)
    if marker:
        return "{}?{}".format(url,
                              urllib.parse.urlencode({marker_name: marker}))

    prev_marker = request.GET.get(prev_marker_name, None)
    if prev_marker:
        return "{}?{}".format(url,
                              urllib.parse.urlencode({prev_marker_name:
                                                      prev_marker}))
    return url
