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
            job_name='tower_launch',
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
                'job_name': 'tower_launch',
                'job_params': {'foo': 'bar'},
                'last_run': '2021-01-01T01:00:00+00:00',
            },
        ],
        'total': 1,
    }


def test_list_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/scheduler/cron',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'description': 'Example cron job',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'tower_launch',
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


def test_create_invalid_job_name(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'time_expr': '0 */2 * * *',
        'job_name': 'foo',
    }

    model.SchedulerCronJob.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/scheduler/cron',
        headers=AUTH_HEADER,
        json=cron_job_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'].startswith(f"{cron_job_data['job_name']!r} is not one of")


@pytest.mark.parametrize(
    'cron_job_data, missing_property',
    [
        pytest.param(
            {
                'name': 'example',
                'time_expr': '0 */2 * * *',
            },
            'job_name',
            id='missing_job_name'
        ),
        pytest.param(
            {
                'time_expr': '0 */2 * * *',
                'job_name': 'tower_launch',
            },
            'name',
            id='missing_name'
        ),
        pytest.param(
            {
                'name': 'example',
                'job_name': 'tower_launch',
            },
            'time_expr',
            id='missing_time_expr'
        ),
    ],
)
def test_create_missing_properties(
    client,
    db_session_mock,
    cron_job_data,
    missing_property
):
    model.SchedulerCronJob.query.filter.return_value.count.return_value = 0

    rv = client.post(
        f'{API_BASE}/scheduler/cron',
        headers=AUTH_HEADER,
        json=cron_job_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'] == f'\'{missing_property}\' is a required property'


def test_create_unauthorized(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'description': 'Example cron job',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'tower_launch',
        'job_params': {'foo': 'bar'},
    }

    rv = client.post(
        f'{API_BASE}/scheduler/cron',
        json=cron_job_data,
    )

    db_session_mock.add.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_create_duplicate_name(client, db_session_mock):
    cron_job_data = {
        'name': 'example',
        'description': 'Example cron job',
        'enabled': True,
        'time_expr': '0 */2 * * *',
        'job_name': 'tower_launch',
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
        job_name='tower_launch',
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
        'job_name': 'tower_launch',
        'job_params': {'foo': 'bar'},
        'last_run': '2021-01-01T01:00:00+00:00',
    }


def test_get_non_existent(client):
    cron_job_id = 1

    model.SchedulerCronJob.query.get.return_value = None

    rv = client.get(
        f'{API_BASE}/scheduler/cron/{cron_job_id}',
        headers=AUTH_HEADER,
    )

    model.SchedulerCronJob.query.get.assert_called_with(cron_job_id)

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'CronJob {cron_job_id} does not exist'


def test_get_unauthorized(client):
    rv = client.get(
        f'{API_BASE}/scheduler/cron/1',
    )

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update(client, db_session_mock):
    cron_job = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='tower_launch',
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


def test_update_non_existent(client, db_session_mock):
    cron_job_id = 1

    model.SchedulerCronJob.query.get.return_value = None

    rv = client.patch(
        f'{API_BASE}/scheduler/cron/{cron_job_id}',
        headers=AUTH_HEADER,
        json={
            'time_expr': '0 */5 * * *',
            'job_params': {'bar': 'foo'},
        },
    )

    model.SchedulerCronJob.query.get.assert_called_with(cron_job_id)

    db_session_mock.commit.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'CronJob {cron_job_id} does not exist'


def test_update_invalid_job_name(client):
    expected_job_name = 'tower_launch'

    cron_job = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name=expected_job_name,
        job_params={'foo': 'bar'},
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )
    model.SchedulerCronJob.query.get.return_value = cron_job

    new_data = {'job_name': 'foo'}

    rv = client.patch(
        f'{API_BASE}/scheduler/cron/{cron_job.id}',
        headers=AUTH_HEADER,
        json=new_data,
    )

    assert cron_job.job_name == expected_job_name

    assert rv.status_code == 400, rv.data
    assert rv.json['title'] == 'Bad Request'
    assert rv.json['detail'].startswith(f"{new_data['job_name']!r} is not one of")


def test_update_unauthorized(client, db_session_mock):
    expected_time_expr = '0 */2 * * *'
    expected_job_params = {'foo': 'bar'}

    cron_job = model.SchedulerCronJob(
        id=1,
        name='example-job',
        description='',
        enabled=True,
        time_expr=expected_time_expr,
        job_name='tower_launch',
        job_params=expected_job_params,
        last_run=datetime.datetime(2021, 1, 1, 1, 0, 0, tzinfo=tzutc()),
    )
    model.SchedulerCronJob.query.get.return_value = cron_job

    rv = client.patch(
        f'{API_BASE}/scheduler/cron/1',
        json={
            'time_expr': '0 */5 * * *',
            'job_params': {'bar': 'foo'},
        },
    )

    db_session_mock.commit.assert_not_called()

    assert cron_job.time_expr == expected_time_expr
    assert cron_job.job_params == expected_job_params

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'


def test_update_duplicate_name(client, db_session_mock):
    cron_job = model.SchedulerCronJob(
        id=1,
        name='example',
        description='',
        enabled=True,
        time_expr='0 */2 * * *',
        job_name='tower_launch',
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
        job_name='tower_launch',
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


def test_delete_non_existent(client, db_session_mock):
    cron_job_id = 1

    model.SchedulerCronJob.query.get.return_value = None

    rv = client.delete(
        f'{API_BASE}/scheduler/cron/{cron_job_id}',
        headers=AUTH_HEADER,
    )

    model.SchedulerCronJob.query.get.assert_called_with(cron_job_id)

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 404, rv.data
    assert rv.json['title'] == 'Not Found'
    assert rv.json['detail'] == f'CronJob {cron_job_id} does not exist'


def test_delete_unauthorized(client, db_session_mock):
    rv = client.delete(
        f'{API_BASE}/scheduler/cron/1',
    )

    db_session_mock.delete.assert_not_called()

    assert rv.status_code == 401, rv.data
    assert rv.json['title'] == 'Unauthorized'
    assert rv.json['detail'] == 'No authorization token provided'
