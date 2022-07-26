import os
import random

import yaml

from rhub.api.bare_metal.host import host_list
from rhub.bare_metal.model import (
    BareMetalHostDrac,
    BareMetalHostRedfish,
)


def read_local_yaml(filename):
    this_filename = os.path.realpath(__file__)
    the_dir = os.path.dirname(this_filename)
    real_filename = the_dir + "/" + filename

    with open(real_filename, "r") as opened:
        parsed = yaml.load(opened, Loader=yaml.Loader)
        return parsed


def get_monitoring_configs():
    configs = read_local_yaml("monitoring_config.yml")
    return configs


def mock_power(type):
    r = []

    configs = get_monitoring_configs()
    available = configs["mock_" + type]

    for platform in available:
        r_platform = {}
        r_platform["platform"] = platform["name"]
        available_platform = platform["available"]

        r_platform["all"] = available_platform

        # to prevent a randrange empty range
        if available_platform == 1:
            available_platform += 1

        on = random.randrange(1, available_platform)

        off = available_platform - on

        r_platform["on"] = on
        r_platform["off"] = off

        r_platform["wattage_on"] = on * configs["base_wattage"]
        r_platform["wattage_off"] = off * configs["base_wattage"]

        r.append(r_platform)

    wrapper = {"data": r}

    return wrapper


def mock_availability(type):
    r = []

    configs = get_monitoring_configs()
    available = configs["mock_" + type]

    for platform in available:
        r_platform = {}
        r_platform["platform"] = platform["name"]
        available_platform = platform["available"]

        r_platform["all"] = available_platform

        # again, to prevent a randrange empty range
        if available_platform == 1:
            available_platform += 1

        random_requested = random.randrange(1, available_platform)

        available_platform -= random_requested

        if available_platform == 1:
            available_platform += 1

        random_provisioned = random.randrange(1, available_platform)

        available_platform -= random_provisioned

        r_platform["requested"] = random_requested
        r_platform["provisioned"] = random_provisioned
        r_platform["available"] = available_platform

        cpus_per_system = platform["cpus_per_system"]
        ram_per_system = platform["ram_per_system"]

        r_platform["cpus_available"] = available_platform * cpus_per_system
        r_platform["memory_available"] = available_platform * ram_per_system

        requested_provisioned = random_requested + random_provisioned
        r_platform["cpus_used"] = requested_provisioned * cpus_per_system
        r_platform["memory_used"] = requested_provisioned * ram_per_system

        r.append(r_platform)

    wrapper = {"data": r}

    return wrapper


def vm_metrics():
    return mock_availability("platforms")


def lab_metrics():
    return mock_availability("products")


def bm_metrics():
    return mock_availability("platforms")


def bm_power_states_metrics():
    return mock_power("platforms")


def bm_hosts_to_monitor_list(host_type="node"):
    nodes_empty = [{"name": "no.nodes.specified"}]

    nodes = []

    if host_type == "node":
        all_hosts = host_list()["data"]

        for host in all_hosts:
            exporter_port = "9100"
            if isinstance(host, BareMetalHostDrac):
                exporter_port = "9101"
            elif isinstance(host, BareMetalHostRedfish):
                exporter_port = "9102"

            host_name = f"{host.name}:{exporter_port}"
            nodes.append({"name": host_name})

    if not nodes:
        nodes = nodes_empty

    r = {}
    r["data"] = nodes

    return r
