import os

import yaml

from rhub.api.utils import choose_from


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

        on = choose_from(available_platform)

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

        random_requested = choose_from(available_platform)

        available_platform -= random_requested

        random_provisioned = choose_from(available_platform)

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


def bm_power_states():
    return mock_power("platforms")


def bm_hosts_to_monitor(target_type="node"):
    nodes = [{"name": "no.nodes.specified"}]

    if target_type == "node":
        nodes_files = read_local_yaml("monitoring_sample_nodes.yml")
        read_nodes = nodes_files["nodes"]
        nodes = []
        for node in read_nodes:
            nodes.append({"name": node})

    r = {}
    r["data"] = nodes

    return r
