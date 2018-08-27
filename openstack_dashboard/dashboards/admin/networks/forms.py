# Copyright 2012 NEC Corporation
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
#
# Copyright (c) 2013-2017 Wind River Systems, Inc.
#

import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from neutronclient.common import exceptions as neutron_exceptions

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api


LOG = logging.getLogger(__name__)

# Predefined provider network types.
# You can add or override these entries by extra_provider_types
# in the settings.
PROVIDER_TYPES = {
    'local': {
        'display_name': _('Local'),
        'require_physical_network': False,
        'require_segmentation_id': False,
    },
    'flat': {
        'display_name': _('Flat'),
        'require_physical_network': True,
        'require_segmentation_id': False,
    },
    'vlan': {
        'display_name': _('VLAN'),
        'require_physical_network': True,
        'require_segmentation_id': True,
    },
    'gre': {
        'display_name': _('GRE'),
        'require_physical_network': False,
        'require_segmentation_id': True,
    },
    'vxlan': {
        'display_name': _('VXLAN'),
        'require_physical_network': False,
        'require_segmentation_id': True,
    },
    'geneve': {
        'display_name': _('Geneve'),
        'require_physical_network': False,
        'require_segmentation_id': True,
    },
    'midonet': {
        'display_name': _('MidoNet'),
        'require_physical_network': False,
        'require_segmentation_id': False,
    },
    'uplink': {
        'display_name': _('MidoNet Uplink'),
        'require_physical_network': False,
        'require_segmentation_id': False,
    },
}
# Predefined valid segmentation ID range per network type.
# You can add or override these entries by segmentation_id_range
# in the settings.
SEGMENTATION_ID_RANGE = {
    'vlan': (1, 4094),
    'gre': (1, (2 ** 32) - 1),
    'vxlan': (1, (2 ** 24) - 1),
    'geneve': (1, (2 ** 24) - 1),
}
# DEFAULT_PROVIDER_TYPES is used when ['*'] is specified
# in supported_provider_types. This list contains network types
# supported by Neutron ML2 plugin reference implementation.
# You can control enabled network types by
# supported_provider_types setting.
DEFAULT_PROVIDER_TYPES = ['local', 'flat', 'vlan', 'gre', 'vxlan', 'geneve']


class CreateNetwork(forms.SelfHandlingForm):
    name = forms.CharField(max_length=255,
                           label=_("Name"),
                           required=False)
    tenant_id = forms.ThemableChoiceField(label=_("Project"))
    network_type = forms.ThemableChoiceField(
        label=_("Provider Network Type"),
        help_text=_("The physical mechanism by which the virtual "
                    "network is implemented."),
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'network_type'
        }))

    physical_network = forms.CharField(
        max_length=255,
        label=_("Physical Network"),
        help_text=_("The name of the physical network over which the "
                    "virtual network is implemented. Specify one of the "
                    "physical networks defined in your neutron deployment."),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
        }))

    physical_network_vlan = forms.ChoiceField(
        label=_("Physical Network"), required=False,
        help_text=_("The name of the physical network over which the "
                    "virtual network is implemented."),
        widget=forms.Select(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-vlan': _('Physical Network')
        }))

    physical_network_vxlan = forms.ChoiceField(
        label=_("Physical Network"), required=False,
        help_text=_("The name of the physical network over which the "
                    "virtual network is implemented."),
        widget=forms.Select(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-vxlan': _('Physical Network'),
        }))

    physical_network_flat = forms.ChoiceField(
        label=_("Physical Network"), required=False,
        help_text=_("The name of the physical network over which the "
                    "virtual network is implemented."),
        widget=forms.Select(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
            'data-network_type-flat': _('Physical Network'),
        }))

    segmentation_id = forms.IntegerField(
        label=_("Segmentation ID"),
        min_value=1,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'network_type',
        }))
    admin_state = forms.BooleanField(label=_("Enable Admin State"),
                                     initial=True,
                                     required=False)
    # QoS policy extension
    qos = forms.ChoiceField(label=_("QoS Policy"), required=False)
    shared = forms.BooleanField(label=_("Shared"),
                                initial=False, required=False)
    external = forms.BooleanField(label=_("External Network"),
                                  initial=False, required=False)
    # VLAN transparency
    vlan_transparent = forms.BooleanField(
        label=_("VLAN Transparent"),
        initial=False, required=False,
        help_text=_("Request that this network be implemented on a provider "
                    "network that supports passing VLAN tagged packets "
                    "transparently."))
    with_subnet = forms.BooleanField(label=_("Create Subnet"),
                                     widget=forms.CheckboxInput(attrs={
                                         'class': 'switchable',
                                         'data-slug': 'with_subnet',
                                         'data-hide-tab': 'create_network__'
                                                          'createsubnetinfo'
                                                          'action,'
                                                          'create_network__'
                                                          'createsubnetdetail'
                                                          'action',
                                         'data-hide-on-checked': 'false'
                                     }),
                                     initial=True,
                                     required=False)

    @classmethod
    def _instantiate(cls, request, *args, **kwargs):
        return cls(request, *args, **kwargs)

    def __init__(self, request, *args, **kwargs):
        super(CreateNetwork, self).__init__(request, *args, **kwargs)
        tenant_choices = [('', _("Select a project"))]
        tenants, has_more = api.keystone.tenant_list(request)
        for tenant in tenants:
            if tenant.enabled:
                tenant_choices.append((tenant.id, tenant.name))
        self.fields['tenant_id'].choices = tenant_choices

        try:
            is_extension_supported = \
                api.neutron.is_extension_supported(request, 'provider')
        except Exception:
            msg = _("Unable to verify Neutron service providers")
            exceptions.handle(self.request, msg)
            self._hide_provider_network_type()
            is_extension_supported = False

        if is_extension_supported:
            neutron_settings = getattr(settings,
                                       'OPENSTACK_NEUTRON_NETWORK', {})
            self.seg_id_range = SEGMENTATION_ID_RANGE.copy()
            seg_id_range = neutron_settings.get('segmentation_id_range')
            if seg_id_range:
                self.seg_id_range.update(seg_id_range)

            self.provider_types = PROVIDER_TYPES.copy()
            extra_provider_types = neutron_settings.get('extra_provider_types')
            if extra_provider_types:
                self.provider_types.update(extra_provider_types)

            self.nettypes_with_seg_id = [
                net_type for net_type in self.provider_types
                if self.provider_types[net_type]['require_segmentation_id']]
            self.nettypes_with_physnet = [
                net_type for net_type in self.provider_types
                if self.provider_types[net_type]['require_physical_network']]

            supported_provider_types = neutron_settings.get(
                'supported_provider_types', DEFAULT_PROVIDER_TYPES)
            if supported_provider_types == ['*']:
                supported_provider_types = DEFAULT_PROVIDER_TYPES

            undefined_provider_types = [
                net_type for net_type in supported_provider_types
                if net_type not in self.provider_types]
            if undefined_provider_types:
                LOG.error('Undefined provider network types are found: %s',
                          undefined_provider_types)

            seg_id_help = [
                _("For %(type)s networks, valid IDs are %(min)s to %(max)s.")
                % {'type': net_type,
                   'min': self.seg_id_range[net_type][0],
                   'max': self.seg_id_range[net_type][1]}
                for net_type in self.nettypes_with_seg_id]
            self.fields['segmentation_id'].help_text = ' '.join(seg_id_help)

            # Register network types which require segmentation ID
            attrs = dict(('data-network_type-%s' % network_type,
                          _('Segmentation ID'))
                         for network_type in self.nettypes_with_seg_id)
            self.fields['segmentation_id'].widget.attrs.update(attrs)

            physical_networks = getattr(settings,
                                        'OPENSTACK_NEUTRON_NETWORK', {}
                                        ).get('physical_networks', [])

            if physical_networks:
                self.fields['physical_network'] = forms.ThemableChoiceField(
                    label=_("Physical Network"),
                    choices=[(net, net) for net in physical_networks],
                    widget=forms.ThemableSelectWidget(attrs={
                        'class': 'switched',
                        'data-switch-on': 'network_type',
                    }),
                    help_text=_("The name of the physical network over "
                                "which the virtual network is implemented."),)

            # Register network types which require physical network
            attrs = dict(('data-network_type-%s' % network_type,
                          _('Physical Network'))
                         for network_type in self.nettypes_with_physnet)
            self.fields['physical_network'].widget.attrs.update(attrs)

            network_type_choices = [
                (net_type, self.provider_types[net_type]['display_name'])
                for net_type in supported_provider_types]
            if len(network_type_choices) == 0:
                self._hide_provider_network_type()
            else:
                self.fields['network_type'].choices = network_type_choices

            if api.base.is_TiS_region(request):
                # Titanium Cloud networktype field choices
                network_type_choices = [('', _("Select a provider "
                                               "network type"))]
                for network_type in \
                        api.neutron.provider_network_type_list(request):
                    network_type_choices.append(
                        (network_type.type, network_type.type))
                self.fields['network_type'].choices = network_type_choices

                net_choices_vlan = []
                net_choices_vxlan = []
                net_choices_flat = []
                for network in api.neutron.provider_network_list(request):
                    if network.type == "vlan":
                        net_choices_vlan.append((network.name, network.name))
                    elif network.type == "vxlan":
                        net_choices_vxlan.append((network.name, network.name))
                    elif network.type == "flat":
                        net_choices_flat.append((network.name, network.name))
                self.fields['physical_network_vlan'].choices = net_choices_vlan
                self.fields['physical_network_vxlan'].choices = \
                    net_choices_vxlan
                self.fields['physical_network_flat'].choices = net_choices_flat
        else:
            self._hide_provider_network_type()

        if api.base.is_TiS_region(request):
            # QoS policy extension
            qos_choices = [('', _("No Policy"))]
            for qos in api.neutron.qos_list(request):
                qos_choices.append((qos.id, qos.name_or_id))
            self.fields['qos'].choices = qos_choices

            del self.fields['physical_network']
        else:
            del self.fields['qos']
            del self.fields['vlan_transparent']
            del self.fields['physical_network_vlan']
            del self.fields['physical_network_vxlan']
            del self.fields['physical_network_flat']

    def _hide_provider_network_type(self):
        self.fields['network_type'].widget = forms.HiddenInput()
        if 'physical_network' in self.fields:
            self.fields['physical_network'].widget = forms.HiddenInput()
            self.fields['physical_network'].required = False
        elif 'physical_network_vlan' in self.fields:
            self.fields['physical_network_vlan'].widget = forms.HiddenInput()
            self.fields['physical_network_vxlan'].widget = forms.HiddenInput()
            self.fields['physical_network_flat'].widget = forms.HiddenInput()
            self.fields['physical_network_vlan'].required = False
            self.fields['physical_network_vxlan'].required = False
            self.fields['physical_network_flat'].required = False

        self.fields['segmentation_id'].widget = forms.HiddenInput()
        self.fields['network_type'].required = False
        self.fields['segmentation_id'].required = False

    def handle(self, request, data):
        try:
            params = {'name': data['name'],
                      'tenant_id': data['tenant_id'],
                      'admin_state_up': data['admin_state'],
                      'shared': data['shared'],
                      'router:external': data['external']}

            # QoS extension
            if api.base.is_TiS_region(request):
                if data.get('qos', None):
                    params['wrs-tm:qos'] = data.get('qos')
                else:
                    params['wrs-tm:qos'] = None

            if api.neutron.is_extension_supported(request, 'vlan-transparent'):
                if 'vlan_transparent' in data:
                    params['vlan_transparent'] = data['vlan_transparent']

            if api.neutron.is_extension_supported(request, 'provider'):
                network_type = data['network_type']
                params['provider:network_type'] = network_type
                if not api.base.is_TiS_region(request):
                    params['provider:physical_network'] = \
                        data['physical_network']
                elif network_type == "vlan":
                    params['provider:physical_network'] = \
                        data['physical_network_vlan']
                elif network_type == "vxlan":
                    params['provider:physical_network'] = \
                        data['physical_network_vxlan']
                elif network_type == "flat":
                    params['provider:physical_network'] = \
                        data['physical_network_flat']
                if network_type != "flat":
                    if data.get('segmentation_id'):
                        params['provider:segmentation_id'] = \
                            data['segmentation_id']
            network = api.neutron.network_create(request, **params)
            LOG.debug('Network %s was successfully created.', data['name'])
            return network
        except neutron_exceptions.NeutronClientException as e:
            LOG.info(e.message)
            redirect = reverse('horizon:admin:networks:index')
            exceptions.handle(request, e.message, redirect=redirect)
        except Exception:
            redirect = reverse('horizon:admin:networks:index')
            msg = _('Failed to create network %s') % data['name']
            exceptions.handle(request, msg, redirect=redirect)

    def clean(self):
        cleaned_data = super(CreateNetwork, self).clean()
        if api.neutron.is_extension_supported(self.request, 'provider'):
            self._clean_physical_network(cleaned_data)
            self._clean_segmentation_id(cleaned_data)
        return cleaned_data

    def _clean_physical_network(self, data):
        network_type = data.get('network_type')

        if api.base.is_TiS_region(self.request):
            if network_type == "vlan":
                if not data.get('physical_network_vlan'):
                    msg = "Physical Network is required for " \
                          "vlan provider network"
                    raise forms.ValidationError(msg)
            elif network_type == "vxlan":
                if not data.get('physical_network_vxlan'):
                    msg = "Physical Network is required for " \
                          "vxlan provider network"
                    raise forms.ValidationError(msg)
            elif network_type == "flat":
                if not data.get('physical_network_flat'):
                    msg = "Physical Network is required for " \
                          "flat provider network"
                    raise forms.ValidationError(msg)

        if ('physical_network' in self._errors and
                network_type not in self.nettypes_with_physnet):
            # In this case the physical network is not required, so we can
            # ignore any errors.
            del self._errors['physical_network']

    def _clean_segmentation_id(self, data):
        network_type = data.get('network_type')
        if 'segmentation_id' in self._errors:
            if (network_type not in self.nettypes_with_seg_id and
                    not self.data.get("segmentation_id")):
                # In this case the segmentation ID is not required, so we can
                # ignore the field is required error.
                del self._errors['segmentation_id']
        elif network_type in self.nettypes_with_seg_id:
            seg_id = data.get('segmentation_id')
            seg_id_range = {'min': self.seg_id_range[network_type][0],
                            'max': self.seg_id_range[network_type][1]}
            if seg_id < seg_id_range['min'] or seg_id > seg_id_range['max']:
                if network_type == 'vlan':
                    if seg_id is None:
                        return
                    msg = _('For VLAN networks, valid VLAN IDs are %(min)s '
                            'through %(max)s.') % seg_id_range
                elif network_type == 'gre':
                    msg = _('For GRE networks, valid tunnel IDs are %(min)s '
                            'through %(max)s.') % seg_id_range
                elif network_type == 'vxlan':
                    msg = _('For VXLAN networks, valid tunnel IDs are %(min)s '
                            'through %(max)s.') % seg_id_range
                self._errors['segmentation_id'] = self.error_class([msg])


class UpdateNetwork(forms.SelfHandlingForm):
    name = forms.CharField(label=_("Name"), required=False)
    admin_state = forms.BooleanField(label=_("Enable Admin State"),
                                     required=False)
    shared = forms.BooleanField(label=_("Shared"), required=False)
    external = forms.BooleanField(label=_("External Network"), required=False)

    # QoS policy extension
    qos = forms.ChoiceField(label=_("QoS Policy"), required=False)

    # VLAN Transparency
    vlan_transparent = forms.BooleanField(label=_("VLAN Transparent"),
                                          required=False)
    vlan_transparent.widget.attrs['disabled'] = 'disabled'

    # Provider extension fields
    providernet_type = forms.CharField(
        label=_("Network Type"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    providernet = forms.CharField(
        label=_("Physical Network"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    segmentation_id = forms.CharField(
        label=_("Segmentation ID"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    failure_url = 'horizon:admin:networks:index'

    def __init__(self, request, *args, **kwargs):
        super(UpdateNetwork, self).__init__(request, *args, **kwargs)

        if api.base.is_TiS_region(self.request):
            # QoS policy extension
            qos_choices = [('', _("No Policy"))]
            for qos in api.neutron.qos_list(request):
                qos_choices.append((qos.id, qos.name_or_id))
            self.fields['qos'].choices = qos_choices
        else:
            del self.fields['qos']
            del self.fields['vlan_transparent']
            del self.fields['providernet_type']
            del self.fields['providernet']
            del self.fields['segmentation_id']

    def handle(self, request, data):
        try:
            params = {'name': data['name'],
                      'admin_state_up': data['admin_state'],
                      'shared': data['shared'],
                      'router:external': data['external']}

            # QoS extension
            if api.base.is_TiS_region(request):
                if data.get('qos', None):
                    params['wrs-tm:qos'] = data.get('qos')
                else:
                    params['wrs-tm:qos'] = None

            network = api.neutron.network_update(request,
                                                 self.initial['network_id'],
                                                 **params)
            msg = _('Network %s was successfully updated.') % data['name']
            messages.success(request, msg)
            return network
        except neutron_exceptions.NeutronClientException as e:
            LOG.info(e.message)
            redirect = reverse(self.failure_url)
            exceptions.handle(request, e.message, redirect=redirect)
        except Exception as e:
            LOG.info('Failed to update network %(id)s: %(exc)s',
                     {'id': self.initial['network_id'], 'exc': e})
            msg = _('Failed to update network %s') % data['name']
            redirect = reverse(self.failure_url)
            exceptions.handle(request, msg, redirect=redirect)
