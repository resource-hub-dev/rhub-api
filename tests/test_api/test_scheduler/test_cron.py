import base64
import datetime

import pytest
from dateutil.tz import tzutc

from rhub.scheduler import model


API_BASE = '/v0'
AUTH_HEADER = {'Authorization': 'Basic X190b2tlbl9fOmR1bW15Cg=='}


def _db_add_row_side_effect(data_added):
    def side_effect(row):
        for k, v in data_added.items():
            setattr(row, k, v)
    return side_effect


def test_list(client):
    model.SchedulerCronJob.query.limit.return_value.offset.return_value = [
        model.SchedulerCronJob(
            id=1,
            name='example-job',
            description='',
            enabled=True,
            time_expr='0 */2 * * *',
            job_name='example',
            job_params={'foo': 'bar'},
            last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
        ),
    ]
    model.SchedulerCronJob.query.count.return_value = 1

    rv = client.get(
        f'{API_BASE}/scheduler/cron',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'data': [
            {
                'id': 1,
                'name': 'example-job',
                'description': '',
                'enabled': True,
                'time_expr': '0 */2 * * *',
                'job_name': 'example',
                'job_params': {'foo': 'bar'},
                'last_run': '2021-01-01T01:00:00+00:00',
            },
        ],
        'total': 1,
    }


def test_create(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'description': 'Example cron job',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'example',
        'job_params': {'foo': 'bar'},
    }

    model.SchedulerCronJob.query.filter.return_value.count.return_value = 0
    db_session_mock.add.side_effect = _db_add_row_side_effect({'id': 1})

    rv = client.post(
        f'{API_BASE}/scheduler/cron',
        headers=AUTH_HEADER,
        json=cron_job_data,
    )

    assert rv.status_code == 200

    db_session_mock.add.assert_called()
    db_session_mock.commit.assert_called()

    cron_job = db_session_mock.add.call_args.args[0]
    for k, v in cron_job_data.items():
        assert getattr(cron_job, k) == v


def test_create_duplicate_name(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'description': 'Example cron job',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'example',
        'job_params': {'foo': 'bar'},
    }

    model.SchedulerCronJob.query.filter.return_value.count.return_value = 1

    rv = client.post(
        f'{API_BASE}/scheduler/cron',
        headers=AUTH_HEADER,
        json=cron_job_data,
    )

    assert rv.status_code == 400
    assert "'example' already exists" in rv.json['detail']


def test_get(client):
    model.SchedulerCronJob.query.get.return_value = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='example',
        job_params={'foo': 'bar'},
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )

    rv = client.get(
        f'{API_BASE}/scheduler/cron/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 200
    assert rv.json == {
        'id': 1,
        'name': 'example-job',
        'description': '',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'example',
        'job_params': {'foo': 'bar'},
        'last_run': '2021-01-01T01:00:00+00:00',
    }


def test_update(client, db_session_mock):
    cron_job = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='example',
        job_params={'foo': 'bar'},
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )
    model.SchedulerCronJob.query.get.return_value = cron_job

    rv = client.patch(
        f'{API_BASE}/scheduler/cron/1',
        headers=AUTH_HEADER,
        json={
            'time_expr': '0 */5 * * *',
            'job_params': {'bar': 'foo'},
        },
    )

    assert rv.status_code == 200

    db_session_mock.commit.assert_called()

    assert cron_job.time_expr == '0 */5 * * *'
    assert cron_job.job_params == {'bar': 'foo'}


def test_update_duplicate_name(client, db_session_mock):
    cron_job = model.SchedulerCronJob(
        id=1,
        name='example',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='example',
        job_params={'foo': 'bar'},
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )
    model.SchedulerCronJob.query.get.return_value = cron_job

    model.SchedulerCronJob.query.filter.return_value.count.return_value = 1

    rv = client.patch(
        f'{API_BASE}/scheduler/cron/1',
        headers=AUTH_HEADER,
        json={
            'name': 'example-duplicate'
        },
    )

    assert rv.status_code == 400
    assert "'example-duplicate' already exists" in rv.json['detail']


def test_delete(client, db_session_mock):
    cron_job = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='example',
        job_params={'foo': 'bar'},
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )
    model.SchedulerCronJob.query.get.return_value = cron_job

    rv = client.delete(
        f'{API_BASE}/scheduler/cron/1',
        headers=AUTH_HEADER,
    )

    assert rv.status_code == 204

    db_session_mock.delete.assert_called_with(cron_job)
    db_session_mock.commit.assert_called()
