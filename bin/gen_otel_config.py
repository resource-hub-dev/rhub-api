#!/usr/bin/env python3

import requests
import os
import urllib3
import json

from pathlib import Path

from pdb import set_trace as stp

DEBUG = False
if "DEBUG" in os.environ:
    if os.environ["DEBUG"].lower() in ["yes", "on", "true"]:
        DEBUG = True

def write_hosts_file(filename, jobname, uri, token):
    print(f"Writing job: {jobname}/{filename}.json...")
    hostlist = call_api(uri, token)
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

    config_file_nodes = f"{config_file_dir}/{filename}.json"
    with open(config_file_nodes, "w") as f:
        json.dump(out_content, f)

script_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = "/".join(script_dir.split("/")[:-1])
config_file_dir = f"{parent_dir}/config"

PATH = '/v0'

HOSTNAME = "https://not.defined.local"
PORT = 443

if DEBUG:
    urllib3.disable_warnings()
    HOSTNAME = "http://10.0.1.30"
    PORT = 8081
    auth = ("admin2", "admin2")
else:
    auth_user = os.environ["USER"]
    auth_pwd = os.environ["PWD"]
    auth = (auth_user, auth_pwd)

def call_api(uri, token=None):
    url = f"{HOSTNAME}:{PORT}{PATH}/{uri}"
    print(f"calling url {url}")
    if None == token:
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

    stage_two = json.loads(stage_one.content.decode("utf-8").replace("'", '"'))
    return stage_two

token_call = call_api("/auth/token/create")
if DEBUG:
    print(token_call)

real_token = token_call["access_token"]


write_hosts_file("otel-all-nodes", "all-nodes", "/monitor/bm/hosts/node", real_token)
write_hosts_file("otel-internal-rhub-exporter", "internal-rhub-exporter", "/monitor/bm/hosts/app", real_token)
