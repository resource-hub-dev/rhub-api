import importlib.resources

import dpath
import yaml


def load_openapi_file(name):
    with importlib.resources.open_text('rhub.openapi', name) as f:
        return yaml.safe_load(f)


def test_scheduler_cronjob_job_name_enum():
    spec = load_openapi_file('scheduler.yml')
    enum_items = dpath.get(spec, 'model/CronJob/properties/job_name/enum')

    from rhub.scheduler import jobs
    job_names = jobs.CronJob.get_jobs()

    assert set(enum_items) == set(job_names)


def test_auth_user_roles_enum():
    spec = load_openapi_file('auth.yml')
    enum_items = dpath.get(spec, 'model/User/properties/roles/items/enum')

    from rhub.auth import model
    roles = (i.value for i in model.Role)

    assert set(enum_items) == set(roles)


def test_lab_clusterstatus_enum():
    spec = load_openapi_file('lab.yml')
    enum_items = dpath.get(spec, 'model/ClusterStatus/enum')

    from rhub.lab import model
    clusterstatus_values = (i.value for i in model.ClusterStatus)

    assert set(enum_items) == set(clusterstatus_values)


def test_lab_clusterstatusflag_enum():
    spec = load_openapi_file('lab.yml')
    enum_items = dpath.get(spec, 'model/ClusterStatusFlag/enum')

    from rhub.lab import model
    clusterstatus_flags = (i.flag for i in model.ClusterStatus)

    assert set(enum_items) == set(clusterstatus_flags)
