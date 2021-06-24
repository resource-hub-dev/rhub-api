import logging

from flask import Response, request, current_app
from connexion import problem
from werkzeug.exceptions import Unauthorized

from rhub.tower import model
from rhub.tower.client import TowerError
from rhub.api import db
from rhub.api.utils import row2dict
from rhub.auth.utils import route_require_admin, user_is_admin


logger = logging.getLogger(__name__)


def _tower_job(db_row, tower_data):
    """
    Utility to format DB row and Tower data into valid TowerJob as defined in
    OpenAPI schema.
    """
    return {
        **row2dict(db_row),
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
    }


def list_servers():
    servers = model.Server.query.all()
    return [row2dict(server) for server in servers], 200


@route_require_admin
def create_server(body, user):
    body.setdefault('description', '')

    server = model.Server(**body)
    db.session.add(server)
    db.session.commit()
    return row2dict(server)


def get_server(server_id):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')
    return row2dict(server)


@route_require_admin
def update_server(server_id, body, user):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    for k, v in body.items():
        setattr(server, k, v)
    db.session.commit()

    return row2dict(server)


@route_require_admin
def delete_server(server_id, user):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    db.session.delete(server)
    db.session.commit()


def list_templates():
    templates = model.Template.query.all()
    return [row2dict(template) for template in templates]


@route_require_admin
def create_template(body, user):
    body.setdefault('description', '')

    template = model.Template(**body)
    db.session.add(template)
    db.session.commit()
    return row2dict(template)


def get_template(template_id):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    try:
        tower_client = template.server.create_tower_client()

        if template.tower_template_is_workflow:
            tower_survey_data = tower_client.workflow_get_survey(
                template.tower_template_id)
        else:
            tower_survey_data = tower_client.template_get_survey(
                template.tower_template_id)

        return {
            **row2dict(template),
            'tower_survey': tower_survey_data,
        }

    except TowerError as e:
        logger.exception(f'Failed to get template data from Tower, {e}')
        return problem(e.response.status_code, 'Error',
                       f'Failed to get template {template_id} data from Tower')

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Uknown server error, {e}')


@route_require_admin
def update_template(template_id, body, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    for k, v in body.items():
        setattr(template, k, v)
    db.session.commit()

    return row2dict(template)


@route_require_admin
def delete_template(template_id, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    db.session.delete(template)
    db.session.commit()


def launch_template(template_id, body, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    try:
        tower_client = template.server.create_tower_client()
        extra_vars = body.get('extra_vars', {})

        logger.info(
            f'Launching tower template {template.id}, extra_vars={extra_vars!r}'
        )
        if template.tower_template_is_workflow:
            tower_job_data = tower_client.workflow_launch(
                template.tower_template_id, extra_vars)
        else:
            tower_job_data = tower_client.template_launch(
                template.tower_template_id, extra_vars)

        job = model.Job(
            template_id=template.id,
            tower_job_id=tower_job_data['id'],
            launched_by=user,
        )
        db.session.add(job)
        db.session.commit()

        return _tower_job(job, tower_job_data)

    except TowerError as e:
        logger.exception(f'Failed to launch tower template, {e}')

        problem_ext = None
        try:
            problem_ext = e.response.json()
            if 'detail' in problem_ext:
                del problem_ext['detail']
        except Exception:
            pass  # simply ignore

        return problem(e.response.status_code, 'Error',
                       f'Failed to launch template {template_id}',
                       ext=problem_ext)

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Uknown server error, {e}')


def list_template_jobs(template_id, user):
    jobs = model.Job.query.filter_by(template_id=template_id)
    if not user_is_admin(user):
        jobs = jobs.filter_by(launched_by=user)
    return [row2dict(job) for job in jobs]


def list_jobs(user):
    if user_is_admin(user):
        jobs = model.Job.query.all()
    else:
        jobs = model.Job.query.filter_by(launched_by=user)
    return [row2dict(job) for job in jobs]


def get_job(job_id, user):
    job = model.Job.query.get(job_id)
    if not job:
        return problem(404, 'Not Found', f'Job {job_id} does not exist')

    if not user_is_admin(user) and job.launched_by != user:
        return problem(403, 'Forbidden',
                       f"You don't have permissions to view job {job_id}")

    try:
        tower_client = job.server.create_tower_client()

        if job.template.tower_template_is_workflow:
            tower_job_data = tower_client.workflow_job_get(job.tower_job_id)
        else:
            tower_job_data = tower_client.template_job_get(job.tower_job_id)

        return _tower_job(job, tower_job_data)

    except TowerError as e:
        logger.exception(f'Failed to get job data from Tower, {e}')
        return problem(e.response.status_code, 'Error',
                       f'Failed to get job {job_id} data from Tower')

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Uknown server error, {e}')


def relaunch_job(job_id, user):
    job = model.Job.query.get(job_id)
    if not job:
        return problem(404, 'Not Found', f'Job {job_id} does not exist')

    if not user_is_admin(user) and job.launched_by != user:
        return problem(403, 'Forbidden',
                       f"You don't have permissions to relaunch job {job_id}")

    try:
        tower_client = job.server.create_tower_client()

        if job.template.tower_template_is_workflow:
            tower_job_data = tower_client.workflow_job_relaunch(job.tower_job_id)
        else:
            tower_job_data = tower_client.template_job_relaunch(job.tower_job_id)

        relaunched_job = model.Job(
            template_id=job.template_id,
            tower_job_id=tower_job_data['id'],
            launched_by=user,
        )
        db.session.add(relaunched_job)
        db.session.commit()

        return _tower_job(relaunched_job, tower_job_data)

    except TowerError as e:
        logger.exception(f'Failed to relaunch job, {e}')

        problem_ext = None
        try:
            problem_ext = e.response.json()
            if 'detail' in problem_ext:
                del problem_ext['detail']
        except Exception:
            pass  # simply ignore

        return problem(e.response.status_code, 'Error',
                       f'Failed to relaunch job {job_id}',
                       ext=problem_ext)

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Uknown server error, {e}')


def get_job_stdout(job_id, user):
    job = model.Job.query.get(job_id)
    if not job:
        return problem(404, 'Not Found', f'Job {job_id} does not exist')

    if not user_is_admin(user) and job.launched_by != user:
        return problem(403, 'Forbidden',
                       f"You don't have permissions to view job {job_id} stdout")

    try:
        tower_client = job.server.create_tower_client()
        tower_job_stdout = tower_client.template_job_stdout(job.tower_job_id)
        # Force text/plain response.
        return Response(tower_job_stdout, 200, content_type='text/plain')

    except TowerError as e:
        logger.exception(f'Failed to get job {job_id} stdout, {e}')
        return problem(e.response.status_code, 'Error',
                       f'Failed to get job {job_id}')

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Uknown server error, {e}')


def webhook_auth(username, password, required_scopes=None):
    # Tower offers sending 'basic' auth credentials to protect access
    # to the webhook_notification() endpoint.  The credentials are
    # defined/stored in Vault.

    try:
        if (username == current_app.config['WEBHOOK_USER']
                and password == current_app.config['WEBHOOK_PASS']):
            return {'sub': 'webhook'}    # successful authentication

    except KeyError as e:
        logger.exception('Missing tower webhook notification credential(s)'
                         f' {e}; notification ignored')

    logger.warning('Incorrect tower webhook notification credentials supplied;'
                   ' notification ignored')

    raise Unauthorized('Incorrect tower webhook notification credentials'
                       ' supplied')


def webhook_notification():
    # See Tower notification documentation for additional information:
    #   https://docs.ansible.com/ansible-tower/latest/html/userguide/
    #       notifications.html#webhook

    # 1) This function should receive the notification payload from Tower [done]
    # 2) Process the payload data: [tbd]
    #     Possibly match on the jobId returned in the payload with a jobId
    #     linked to a cluster stored in the DB?
    #      - get_cluster_info(id) [if more information on the cluster is needed]
    # 3) Notify the user of an event: [tbd]
    #      - app.io.emit(popup_message,data)
    #      - update_cluster_status(id)  [database operation]
    #      - send_email(user.email, message) or submit the notification to Hydra?

    # inspect json payload to ensure certain fields are present
    try:
        jobId = request.json['id']
        jobStatus = request.json['status']
    except Exception as e:
        logger.exception(f'Unexpected tower webhook notification json; missing {e}')
        return problem(400, 'Unexpected tower webhook notification json',
                            'JSON payload missing required field(s)',
                            ext={'missing': str(e)})

    logger.info(f'Received a notification from tower {jobId, jobStatus}')

    # Notify the user that something has occurred...
    # Do something here...TBD...
    pass

    return Response(status=204)
