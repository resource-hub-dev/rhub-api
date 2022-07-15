#!/usr/bin/env python3

# This program writes configs for OTEL so we can start that with
# the right list of exporters for Prometheus-like federation.
import os
import json

import requests
import urllib3


def load_config():
    r = {}

    DEBUG = False
    if "DEBUG" in os.environ:
        if os.environ["DEBUG"].lower() in ["yes", "on", "true"]:
            DEBUG = True

    if DEBUG:
        urllib3.disable_warnings()
        hostname = "http://rhub-api"
        if "RHUB_API_HOSTNAME" in os.environ:
            hostname = os.environ["RHUB_API_HOSTNAME"]
        port = 8081
        auth = ("admin2", "admin2")
    else:
        hostname = os.environ["RHUB_API_HOSTNAME"]
        port = os.environ["RHUB_API_PORT"]
        auth_user = os.environ["RHUB_API_USER"]
        auth_pwd = os.environ["RHUB_API_PWD"]
        auth = (auth_user, auth_pwd)

    script_dir = os.path.abspath(os.path.dirname(__file__))
    # one level up from current path
    parent_dir = "/".join(script_dir.split("/")[:-1])
    config_file_dir = f"{parent_dir}/config"

    r["config_file_dir"] = config_file_dir
    r["auth"] = auth
    r["hostname"] = hostname
    r["path"] = '/v0'
    r["port"] = port
    r["DEBUG"] = DEBUG

    return r


def write_hosts_file(config, filename, jobname, uri, token):
    print(f"Writing job: {jobname}/{filename}.json...")
    hostlist = call_api(config, uri, token)
    data = hostlist["data"]
    all_hosts = []
    for host_info in data:
        host_name = host_info["name"]
        all_hosts.append(host_name)

    out_h = {
        "labels": {
            "job": jobname
        },
        "targets": all_hosts
    }
    out_content = [out_h]

    config_file_dir = config["config_file_dir"]

    config_file_nodes = f"{config_file_dir}/{filename}.json"
    with open(config_file_nodes, "w") as f:
        json.dump(out_content, f)


def call_api(config, uri, token=None):
    DEBUG = config["DEBUG"]
    hostname = config["hostname"]
    port = config["port"]
    path = config["path"]
    auth = config["auth"]

    url = f"{hostname}:{port}{path}/{uri}"
    print(f"calling rl {url}")

    if token is None:
        stage_one = requests.post(url, auth=auth, timeout=2, verify=False)
    else:
        stage_one = requests.get(
            url,
            timeout=2,
            headers={"Authorization": "Bearer " + token},
            verify=False
        )

    if DEBUG:
        print(stage_one)

    decoded = stage_one.content.decode("utf-8").replace("'", '"')
    stage_two = json.loads(decoded)
    return stage_two


def main():
    config = load_config()
    DEBUG = config["DEBUG"]

    token_call = call_api(config, "/auth/token/create")
    if DEBUG:
        print(token_call)

    real_token = token_call["access_token"]

    write_hosts_file(config,
                     "otel-all-nodes",
                     "all-nodes",
                     "/monitor/bm/hosts/node", real_token)
    write_hosts_file(config,
                     "otel-internal-rhub-exporter",
                     "internal-rhub-exporter",
                     "/monitor/bm/hosts/app", real_token)


if __name__ == "__main__":
    main()
