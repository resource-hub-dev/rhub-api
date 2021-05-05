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

    def __attrs_post_init__(self):
        self.url = self.url.rstrip('/')

        self._session = requests.Session()
        self._session.auth = (self.username, self.password)

    def request(self, method, path, params=None, data=None):
        """
        Make request to Tower API.

        Returns: requests.Response
        Raises: TowerError if request failed (HTTP status code 4** or 5**)
        """
        path = path.lstrip('/')
        headers = {'Content-Type': 'application/json'}

        response = self._session.request(
            method=method,
            url=f'{self.url}/api/v2/{path}',
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

    def template_get(self, template_id):
        """
        Get job template data.

        Returns: dict
        Raises: TowerError
        """
        return self.request('GET', f'/job_templates/{template_id}/').json()

    def workflow_get(self, workflow_id):
        """
        Get workflow job data.

        Returns: dict
        Raises: TowerError
        """
        return self.request('GET', f'/workflow_job_templates/{workflow_id}/').json()

    def template_get_survey(self, template_id):
        """
        Get job template survey spec.

        Returns: dict
        Raises: TowerError
        """
        return self.request(
            'GET',
            f'/job_templates/{template_id}/survey_spec/',
        ).json()

    def workflow_get_survey(self, workflow_id):
        """
        Get workflow job survey spec.

        Returns: dict
        Raises: TowerError
        """
        return self.request(
            'GET',
            f'/workflow_job_templates/{workflow_id}/survey_spec/',
        ).json()

    def template_launch(self, template_id, extra_vars=None):
        """
        Launch job template.

        Returns: dict - job data
        Raises: TowerError
        """
        return self.request(
            'POST',
            f'/job_templates/{template_id}/launch/',
            data={
                'extra_vars': extra_vars or {},
            },
        ).json()

    def workflow_launch(self, workflow_id, extra_vars=None):
        """
        Launch workflow job.

        Returns: dict - workflow job data
        Raises: TowerError
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

        Returns: dict
        Raises: TowerError
        """
        return self.request('GET', f'/jobs/{template_job_id}/').json()

    def workflow_job_get(self, workflow_job_id):
        """
        Get workflow job (launched workflow job).

        Returns: dict
        Raises: TowerError
        """
        return self.request('GET', f'/workflow_jobs/{workflow_job_id}/').json()

    def template_job_relaunch(self, template_job_id):
        """
        Relaunch job.

        Returns: dict - job data
        Raises: TowerError
        """
        return self.request(
            'POST',
            f'/jobs/{template_job_id}/relaunch/',
        ).json()

    def workflow_job_relaunch(self, workflow_job_id):
        """
        Relaunch workflow job.

        Returns: dict - workflow job data
        Raises: TowerError
        """
        return self.request(
            'POST',
            f'/workflow_jobs/{workflow_job_id}/relaunch/',
        ).json()

    def template_job_stdout(self, template_job_id, output_format='txt'):
        """
        Get job stdout (output from Ansible).

        Returns: dict if output_format is json otherwise str
        Raises: TowerError
        """
        response = self.request(
            'GET',
            f'/jobs/{template_job_id}/stdout/',
            params={'format': output_format},
        )
        if output_format == 'json':
            return response.json()
        return response.text
