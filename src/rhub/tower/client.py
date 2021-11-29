import requests
import attr


class TowerError(requests.HTTPError):
    pass


@attr.s
class Tower:
    """Tower API client."""

    url = attr.ib()
    username = attr.ib()
    password = attr.ib(repr=False)
    verify_ssl = attr.ib(default=True)

    def __attrs_post_init__(self):
        self.url = self.url.rstrip('/')

        self._session = requests.Session()
        self._session.auth = (self.username, self.password)

    def request(self, method, path, params=None, data=None):
        """
        Make request to Tower API.

        :returns: requests.Response
        :raises: TowerError if request failed (HTTP status code 4** or 5**)
        """
        path = path.lstrip('/')
        headers = {'Content-Type': 'application/json'}

        response = self._session.request(
            method=method,
            url=f'{self.url}/api/v2/{path}',
            verify=self.verify_ssl,
            headers=headers,
            params=params,
            json=data,
        )

        if not response.ok:
            raise TowerError(
                f'{response.status_code} Error: {response.reason} '
                f'for url: {response.url}',
                response=response,
            )

        return response

    def ping(self):
        """Ping Tower API and get basic info about cluster."""
        return self.request('GET', '/ping').json()

    def template_get(self, template_id=None, template_name=None):
        """
        Get job template data.

        :returns: dict
        :raises: TowerError
        """
        if template_id is not None:
            return self.request('GET', f'/job_templates/{template_id}/').json()

        elif template_name is not None:
            response = self.request('GET', '/job_templates/',
                                    params={'name': template_name})
            data = response.json()
            if data['count'] != 1:
                raise TowerError(f'Template with name {template_name!r} not found',
                                 response=response)
            return data['results'][0]

        raise TypeError("Missing required argument 'template_id' or 'template_name'")

    def workflow_get(self, workflow_id=None, workflow_name=None):
        """
        Get workflow job data.

        :returns: dict
        :raises: TowerError
        """
        if workflow_id is not None:
            return self.request('GET', f'/workflow_job_templates/{workflow_id}/').json()

        elif workflow_name is not None:
            response = self.request('GET', '/workflow_job_templates/',
                                    params={'name': workflow_name})
            data = response.json()
            if data['count'] != 1:
                raise TowerError(f'Workflow with name {workflow_name!r} not found',
                                 response=response)
            return data['results'][0]

        raise TypeError("Missing required argument 'workflow_id' or 'workflow_name'")

    def template_get_survey(self, template_id):
        """
        Get job template survey spec.

        :returns: dict
        :raises: TowerError
        """
        return self.request(
            'GET',
            f'/job_templates/{template_id}/survey_spec/',
        ).json()

    def workflow_get_survey(self, workflow_id):
        """
        Get workflow job survey spec.

        :returns: dict
        :raises: TowerError
        """
        return self.request(
            'GET',
            f'/workflow_job_templates/{workflow_id}/survey_spec/',
        ).json()

    def template_launch(self, template_id, template_launch_params=None):
        """
        Launch job template.

        :returns: dict - job data
        :raises: TowerError
        """
        return self.request(
            'POST',
            f'/job_templates/{template_id}/launch/',
            data=template_launch_params or {},
        ).json()

    def workflow_launch(self, workflow_id, extra_vars=None):
        """
        Launch workflow job.

        :returns: dict - workflow job data
        :raises: TowerError
        """
        return self.request(
            'POST',
            f'/workflow_job_templates/{workflow_id}/launch/',
            data={
                'extra_vars': extra_vars or {},
            },
        ).json()

    def template_job_get(self, template_job_id):
        """
        Get job (launched job template).

        :returns: dict
        :raises: TowerError
        """
        return self.request('GET', f'/jobs/{template_job_id}/').json()

    def workflow_job_get(self, workflow_job_id):
        """
        Get workflow job (launched workflow job).

        :returns: dict
        :raises: TowerError
        """
        return self.request('GET', f'/workflow_jobs/{workflow_job_id}/').json()

    def template_job_relaunch(self, template_job_id):
        """
        Relaunch job.

        :returns: dict - job data
        :raises: TowerError
        """
        return self.request(
            'POST',
            f'/jobs/{template_job_id}/relaunch/',
        ).json()

    def workflow_job_relaunch(self, workflow_job_id):
        """
        Relaunch workflow job.

        :returns: dict - workflow job data
        :raises: TowerError
        """
        return self.request(
            'POST',
            f'/workflow_jobs/{workflow_job_id}/relaunch/',
        ).json()

    def template_job_stdout(self, template_job_id, output_format='txt'):
        """
        Get job stdout (output from Ansible).

        :returns: dict if output_format is json otherwise str
        :raises: TowerError
        """
        response = self.request(
            'GET',
            f'/jobs/{template_job_id}/stdout/',
            params={'format': output_format},
        )
        if output_format == 'json':
            return response.json()
        return response.text
