from unittest.mock import ANY
from contextlib import contextmanager

import pytest

API_BASE = '/v0'


def test_bm_list_hosts(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/node',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json

    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/app',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_bm_power_states_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/power_states_metrics',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_bm_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/metrics',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_vm_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/vm/metrics',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_lab_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/lab/metrics',
        headers={'Authorization': 'Bearer foobar'},
    )

    assert rv.status_code == 200
    assert "data" in rv.json


@contextmanager
def does_not_raise():
    yield
