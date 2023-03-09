from unittest.mock import ANY
from contextlib import contextmanager

import pytest

API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def test_bm_list_hosts(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/node',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json

    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/app',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_bm_list_hosts_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/node',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'

    rv = client.get(
        f'{API_BASE}/monitor/bm/hosts/app',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_bm_power_states_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/power_states_metrics',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_bm_power_states_metrics_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/power_states_metrics',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_bm_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/metrics',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_bm_metrics_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/monitor/bm/metrics',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_vm_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/vm/metrics',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_vm_metrics_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/monitor/vm/metrics',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_lab_metrics(client):
    rv = client.get(
        f'{API_BASE}/monitor/lab/metrics',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert "data" in rv.json


def test_lab_metrics_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/monitor/lab/metrics',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


@contextmanager
def does_not_raise():
    yield
