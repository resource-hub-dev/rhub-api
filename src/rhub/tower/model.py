from sqlalchemy.dialects import postgresql

from rhub.api import db, get_vault
from rhub.tower.client import Tower
from rhub.api.utils import ModelMixin


class Server(db.Model, ModelMixin):
    __tablename__ = 'tower_server'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    url = db.Column(db.String(256), nullable=False)
    #: Tower credentials path (Vault mount/path)
    credentials = db.Column(db.String(256), nullable=False)

    def create_tower_client(self) -> Tower:
        """
        Create Tower client.

        :returns: :class:`rhub.tower.client.Tower`
        :raises: `RuntimeError` if failed to create client due to missing
                 credentials in vault
        :raises: `Exception` any other errors
        """
        credentials = get_vault().read(self.credentials)
        if not credentials:
            raise RuntimeError('Missing credentials in vault')
        return Tower(
            url=self.url,
            username=credentials['username'],
            password=credentials['password'],
        )


class Template(db.Model, ModelMixin):
    __tablename__ = 'tower_template'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    #: Reference to Tower server (:attr:`Server.id`).
    server_id = db.Column(db.Integer, db.ForeignKey('tower_server.id'),
                          nullable=False)
    #: ID of template in Tower.
    tower_template_id = db.Column(db.Integer, nullable=False)
    #: Is template workflow?
    tower_template_is_workflow = db.Column(db.Boolean, nullable=False)

    #: :type: list of :class:`Job`
    jobs = db.relationship('Job', back_populates='template')
    #: :type: :class:`Server`
    server = db.relationship('Server')


class Job(db.Model, ModelMixin):
    __tablename__ = 'tower_job'

    id = db.Column(db.Integer, primary_key=True)
    #: Reference to Tower template (:attr:`Template.id`).
    template_id = db.Column(db.Integer, db.ForeignKey('tower_template.id'),
                            nullable=False)
    #: ID of job in Tower.
    tower_job_id = db.Column(db.Integer, nullable=False)
    #: UUID of user who launched job.
    #: See: :meth:`rhub.auth.keycloak.KeycloakClient.user_get`.
    #:
    #: :type: `str`
    launched_by = db.Column(postgresql.UUID, nullable=False, index=True)

    #: :type: :class:`Template`
    template = db.relationship('Template')

    @property
    def server(self):
        return self.template.server
