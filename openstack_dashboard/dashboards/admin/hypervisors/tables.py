# Copyright 2013 B1 Systems GmbH
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

from django import template
from django.utils.translation import ugettext_lazy as _

from horizon import tables
from horizon.templatetags import sizeformat
from openstack_dashboard.utils import objectify


def get_cpu_model(hypervisor):
    if hasattr(hypervisor, "cpu_info"):
        vendor = hypervisor.cpu_info.get("vendor", "n/a")
        model = hypervisor.cpu_info.get("model", "n/a")
        return "{}/{}".format(vendor, model)
    else:
        return _("n/a")


def get_status(hypervisor):
    if hasattr(hypervisor, "status"):
        status = hypervisor.status
        return status
    else:
        return _("Hypervisor has no status")


def get_vcpus_used(hypervisor):
    template_name = 'admin/hypervisors/_vcpus_used.html'

    vcpus_used_info = []
    vcpus_used_by_node = getattr(hypervisor, "vcpus_used_by_node", None)
    vcpus_by_node = getattr(hypervisor, "vcpus_by_node", None)

    if vcpus_used_by_node and vcpus_by_node:
        vcpus_used_by_node = eval(vcpus_used_by_node)
        vcpus_by_node = eval(vcpus_by_node)
        for key, value in vcpus_used_by_node.iteritems():
            _info = objectify.objectify(value)
            _info.vcpu = vcpus_by_node[key]
            _info.node = key
            vcpus_used_info.append(_info)
        vcpus_used_info = sorted(vcpus_used_info, key=lambda m: m.node)

    context = {
        "vcpus_used": hypervisor.vcpus_used,
        "id": hypervisor.id,
        "vcpus_used_info": vcpus_used_info
    }
    return template.loader.render_to_string(template_name, context)


def get_memory_used(hypervisor):
    template_name = 'admin/hypervisors/_memory_used.html'

    memory_used_info = []
    memory_used_by_node = getattr(hypervisor, "memory_mb_used_by_node", None)

    if memory_used_by_node:
        memory_used_by_node = eval(memory_used_by_node)
        for key, value in memory_used_by_node.iteritems():
            _info = objectify.objectify(value)
            _info.node = key
            memory_used_info.append(_info)
        memory_used_info = sorted(memory_used_info, key=lambda m: m.node)

    memory_used = _("%sMB") % hypervisor.memory_mb_used

    context = {
        "memory_used": memory_used,
        "id": hypervisor.id,
        "memory_used_info": memory_used_info
    }
    return template.loader.render_to_string(template_name, context)


def get_memory_total(hypervisor):
    template_name = 'admin/hypervisors/_memory_total.html'

    memory_total_info = []
    memory_mb_by_node = getattr(hypervisor, "memory_mb_by_node", None)

    if memory_mb_by_node:
        memory_mb_by_node = eval(memory_mb_by_node)
        for key, value in memory_mb_by_node.iteritems():
            _info = objectify.objectify(value)
            _info.node = key
            memory_total_info.append(_info)

        memory_total_info = sorted(memory_total_info, key=lambda m: m.node)

    memory_total = _("%sMB") % hypervisor.memory_mb

    context = {
        "memory_total": memory_total,
        "id": hypervisor.id,
        "memory_total_info": memory_total_info

    }
    return template.loader.render_to_string(template_name, context)


class AdminHypervisorsTable(tables.DataTable):
    STATUS_CHOICES = (
        ("enabled", True),
        ("down", False),
        ("disabled", False),
    )

    hostname = tables.WrappingColumn("hypervisor_hostname",
                                     link="horizon:admin:hypervisors:detail",
                                     verbose_name=_("Hostname"))

    cpu_model = tables.Column(get_cpu_model,
                              verbose_name=_("CPU"))

    hypervisor_type = tables.Column("hypervisor_type",
                                    verbose_name=_("Type"))

    vcpus_used = tables.Column(get_vcpus_used,
                               verbose_name=_("VCPUs (used)"),
                               attrs={'data-type': 'vcpus_used'})

    vcpus = tables.Column("vcpus",
                          verbose_name=_("VCPUs (total)"))

    memory_used = tables.Column(get_memory_used,
                                verbose_name=_("RAM (used)"),
                                attrs={'data-type': 'size'},
                                filters=(sizeformat.mb_float_format,))

    memory = tables.Column(get_memory_total,
                           verbose_name=_("RAM (total)"),
                           attrs={'data-type': 'size'},
                           filters=(sizeformat.mb_float_format,))

    local_used = tables.Column('local_gb_used',
                               verbose_name=_("Local Storage (used)"),
                               attrs={'data-type': 'size'},
                               filters=(sizeformat.diskgbformat,))

    local = tables.Column('local_gb',
                          verbose_name=_("Local Storage (total)"),
                          attrs={'data-type': 'size'},
                          filters=(sizeformat.diskgbformat,))

    running_vms = tables.Column("running_vms",
                                verbose_name=_("Instances"))

    status = tables.Column(get_status,
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES)

    def get_object_id(self, hypervisor):
        return "%s_%s" % (hypervisor.id,
                          hypervisor.hypervisor_hostname)

    class Meta(object):
        name = "hypervisors"
        verbose_name = _("Hypervisors")
        status_columns = ["status"]


class AdminHypervisorInstancesTable(tables.DataTable):
    name = tables.WrappingColumn("name",
                                 link="horizon:admin:instances:detail",
                                 verbose_name=_("Instance Name"))

    instance_id = tables.Column("uuid",
                                verbose_name=_("Instance ID"))

    def get_object_id(self, server):
        return server['uuid']

    class Meta(object):
        name = "hypervisor_instances"
        verbose_name = _("Hypervisor Instances")
