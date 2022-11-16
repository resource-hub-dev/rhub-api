import json
import logging
import time

from connexion import problem
from flask import Response, request, url_for

from rhub.api import DEFAULT_PAGE_LIMIT, db, di
from rhub.api.utils import date_now, db_sort
from rhub.auth.utils import route_require_admin, user_is_admin
from rhub.lab import model as lab_model
from rhub.messaging import Messaging
from rhub.tower import model
from rhub.tower.client import TowerError


logger = logging.getLogger(__name__)


def _tower_job(db_row, tower_data):
    """
    Utility to format DB row and Tower data into valid TowerJob as defined in
    OpenAPI schema.
    """
    return {
        **db_row.to_dict(),
        'status': tower_data['status'],
        'created_at': tower_data['created'],
        'started': tower_data['started'] is not None,
        'started_at': tower_data['started'],
        'finished': tower_data['finished'] is not None,
        'finished_at': tower_data['finished'],
        'failed': tower_data['failed'],
    }


def _server_href(server):
    href = {
        'server': url_for('.rhub_api_tower_get_server',
                          server_id=server.id),
    }
    return href


def _template_href(template):
    href = {
        'template': url_for('.rhub_api_tower_get_template',
                            template_id=template.id),
        'template_launch': url_for('.rhub_api_tower_launch_template',
                                   template_id=template.id),
        'template_jobs': url_for('.rhub_api_tower_list_template_jobs',
                                 template_id=template.id),
    }
    return href | _server_href(template.server)


def _job_href(job):
    href = {
        'job': url_for('.rhub_api_tower_get_job',
                       job_id=job.id),
        'job_stdout': url_for('.rhub_api_tower_get_job_stdout',
                              job_id=job.id),
        'job_relaunch': url_for('.rhub_api_tower_relaunch_job',
                                job_id=job.id),
    }
    return href | _template_href(job.template)


def list_servers(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    servers = model.Server.query

    if 'name' in filter_:
        servers = servers.filter(model.Server.name.ilike(filter_['name']))

    if sort:
        servers = db_sort(servers, sort)

    return {
        'data': [
            server.to_dict() | {'_href': _server_href(server)}
            for server in servers.limit(limit).offset(page * limit)
        ],
        'total': servers.count(),
    }


@route_require_admin
def create_server(body, user):
    body.setdefault('description', '')

    query = model.Server.query.filter(model.Server.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Server with name {body["name"]!r} already exists',
        )

    server = model.Server.from_dict(body)

    db.session.add(server)
    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) created by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )

    return server.to_dict() | {'_href': _server_href(server)}


def get_server(server_id):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')
    return server.to_dict() | {'_href': _server_href(server)}


@route_require_admin
def update_server(server_id, body, user):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    server.update_from_dict(body)
    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) updated by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )

    return server.to_dict() | {'_href': _server_href(server)}


@route_require_admin
def delete_server(server_id, user):
    server = model.Server.query.get(server_id)
    if not server:
        return problem(404, 'Not Found', f'Server {server_id} does not exist')

    db.session.delete(server)
    db.session.commit()

    logger.info(
        f'Server {server.name} (id {server.id}) deleted by user {user}',
        extra={'user_id': user, 'server_id': server.id},
    )


def list_templates(filter_, sort=None, page=0, limit=DEFAULT_PAGE_LIMIT):
    templates = model.Template.query

    if 'name' in filter_:
        templates = templates.filter(model.Template.name.ilike(filter_['name']))

    if 'server_id' in filter_:
        templates = templates.filter(model.Template.server_id == filter_['server_id'])

    if sort:
        templates = db_sort(templates, sort)

    return {
        'data': [
            template.to_dict() | {'_href': _template_href(template)}
            for template in templates.limit(limit).offset(page * limit)
        ],
        'total': templates.count(),
    }


@route_require_admin
def create_template(body, user):
    body.setdefault('description', '')

    query = model.Template.query.filter(model.Template.name == body['name'])
    if query.count() > 0:
        return problem(
            400, 'Bad Request',
            f'Template with name {body["name"]!r} already exists',
        )

    template = model.Template.from_dict(body)

    db.session.add(template)
    db.session.commit()

    logger.info(
        f'Template {template.name} (id {template.id}) created by user {user}',
        extra={'user_id': user, 'template_id': template.id},
    )

    return template.to_dict() | {'_href': _template_href(template)}


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

        return template.to_dict() | {
            'tower_survey': tower_survey_data,
            '_href': _template_href(template),
        }

    except TowerError as e:
        logger.exception(f'Failed to get template data from Tower, {e}')
        return problem(e.response.status_code, 'Error',
                       f'Failed to get template {template_id} data from Tower')

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Unknown server error, {e}')


@route_require_admin
def update_template(template_id, body, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    template.update_from_dict(body)
    db.session.commit()

    logger.info(
        f'Template {template.name} (id {template.id}) updated by user {user}',
        extra={'user_id': user, 'template_id': template.id},
    )

    return template.to_dict() | {'_href': _template_href(template)}


@route_require_admin
def delete_template(template_id, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    db.session.delete(template)
    db.session.commit()

    logger.info(
        f'Template {template.name} (id {template.id}) deleted by user {user}',
        extra={'user_id': user, 'template_id': template.id},
    )


def launch_template(template_id, body, user):
    template = model.Template.query.get(template_id)
    if not template:
        return problem(404, 'Not Found', f'Template {template_id} does not exist')

    try:
        tower_client = template.server.create_tower_client()
        template_launch_params = body

        logger.info(
            f'Launching tower template {template.id}'
            f'template_launch_params={template_launch_params!r}',
            extra={'user_id': user},
        )
        if template.tower_template_is_workflow:
            tower_job_data = tower_client.workflow_launch(
                template.tower_template_id, template_launch_params)
        else:
            tower_job_data = tower_client.template_launch(
                template.tower_template_id, template_launch_params)

        job = model.Job(
            template_id=template.id,
            tower_job_id=tower_job_data['id'],
            launched_by=user,
        )
        db.session.add(job)
        db.session.commit()

        return _tower_job(job, tower_job_data) | {'_href': _job_href(job)}

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
        return problem(500, 'Server Error', f'Unknown server error, {e}')


def list_template_jobs(template_id, user, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    jobs = model.Job.query.filter(model.Job.template_id == template_id)

    if not user_is_admin(user):
        jobs = jobs.filter(model.Job.launched_by == user)

    if 'launched_by' in filter_:
        jobs = jobs.filter(model.Job.launched_by == filter_['launched_by'])

    return {
        'data': [
            job.to_dict() | {'_href': _job_href(job)}
            for job in jobs.limit(limit).offset(page * limit)
        ],
        'total': jobs.count(),
    }


def list_jobs(user, filter_, page=0, limit=DEFAULT_PAGE_LIMIT):
    jobs = model.Job.query

    if not user_is_admin(user):
        jobs = jobs.filter(model.Job.launched_by == user)

    if 'launched_by' in filter_:
        jobs = jobs.filter(model.Job.launched_by == filter_['launched_by'])

    return {
        'data': [
            job.to_dict() | {'_href': _job_href(job)}
            for job in jobs.limit(limit).offset(page * limit)
        ],
        'total': jobs.count(),
    }


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

        return _tower_job(job, tower_job_data) | {'_href': _job_href(job)}

    except TowerError as e:
        logger.exception(f'Failed to get job data from Tower, {e}')
        return problem(e.response.status_code, 'Error',
                       f'Failed to get job {job_id} data from Tower')

    except Exception as e:
        logger.exception(e)
        return problem(500, 'Server Error', f'Unknown server error, {e}')


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

        logger.info(
            f'Re-launching tower job {tower_job_data["id"]}',
            extra={'user_id': user},
        )

        return _tower_job(relaunched_job, tower_job_data) | {'_href': _job_href(job)}

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
        return problem(500, 'Server Error', f'Unknown server error, {e}')


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
        return problem(500, 'Server Error', f'Unknown server error, {e}')


def webhook_notification():
    payload = request.json

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

    # if this is a test notification from Tower, allow it to succeed
    body = payload.get('body', '')
    if 'Ansible Tower Test Notification' in body:
        logger.info(f'Received a test notification from tower ({body})')
        return Response(status=204)

    job_id = payload.get('id')
    job_status = payload.get('status')
    job_url = payload.get('url')
    if not job_id or not job_status:
        logger.error('Unexpected tower webhook notification data')
        return Response(status=400)

    logger.info(
        f'Received a notification from tower {job_id=} {job_status=} {job_url=}'
    )

    if job_url and '/jobs/project/' in job_url:
        return Response(status=204)

    try:
        extra_vars = json.loads(payload['extra_vars'])

        # Notification from cluster create/delete job have `rhub_cluster_id`
        # extra var.
        if rhub_cluster_id := extra_vars.get('rhub_cluster_id'):
            cluster_notification_handler(payload, rhub_cluster_id)

    except Exception:
        logger.exception(
            f'Failed to process a notification from tower {job_id=} {job_status=}'
        )

    return Response(status=204)


def cluster_notification_handler(payload, cluster_id):
    messaging = di.get(Messaging)

    cluster = lab_model.Cluster.query.get(cluster_id)
    tower_client = cluster.region.tower.create_tower_client()

    job_id = payload['id']
    job_name = payload['name']
    job_status = payload['status']

    # If received notification and status is running, wait a few seconds and
    # then check status of the job. Sometimes a job fails almost immediatelly
    # after it started and does not send failure notification.
    if job_status == 'running':
        time.sleep(5)
        job = tower_client.template_job_get(job_id)
        if job['failed']:
            job_status = 'failed'

    if job_name == cluster.product.tower_template_name_create:
        cluster_operation = 'create'
    elif job_name == cluster.product.tower_template_name_delete:
        cluster_operation = 'delete'
    else:
        return

    def update_cluster_status(new_status):
        if cluster.status != new_status:
            cluster_event = lab_model.ClusterStatusChangeEvent(
                cluster_id=cluster.id,
                user_id=None,
                date=date_now(),
                old_value=cluster.status,
                new_value=new_status,
            )
            db.session.add(cluster_event)
            cluster.status = new_status
            db.session.commit()

    msg_extra = {
        'owner_id': cluster.owner_id,
        'owner_name': cluster.owner_name,
        'cluster_id': cluster.id,
        'cluster_name': cluster.name,
        'tower_id': cluster.region.tower_id,
        'job_id': job_id,
        'job_status': job_status,
    }

    if job_status == 'successful':
        messaging.send(
            f'lab.cluster.{cluster_operation}',
            f'Cluster "{cluster.name}" (ID={cluster.id}) has been successfully '
            f'{cluster_operation}d.',
            extra=msg_extra,
        )
        if cluster_operation == 'create':
            update_cluster_status(lab_model.ClusterStatus.ACTIVE)
        else:
            update_cluster_status(lab_model.ClusterStatus.DELETED)

    elif job_status == 'failed':
        messaging.send(
            f'lab.cluster.{cluster_operation}',
            f'Failed to {cluster_operation} cluster "{cluster.name}" '
            f'(ID={cluster.id}).',
            extra=msg_extra,
        )
        if not cluster.status.is_failed:
            if cluster_operation == 'create':
                update_cluster_status(lab_model.ClusterStatus.CREATE_FAILED)
            else:
                update_cluster_status(lab_model.ClusterStatus.DELETE_FAILED)
